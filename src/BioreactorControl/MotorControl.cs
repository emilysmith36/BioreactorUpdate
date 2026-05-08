namespace BioreactorControl.Motors;

using BioreactorControl.Backend;
using BioreactorControl.Projects;

public enum MotorState
{
    Idle,
    Ready,
    Moving,
    Jogging,
    Running,
    Paused,
    Stopped,
    Error
}

public sealed class JogResumeCommand
{
    public string Motor { get; init; } = string.Empty;
    public float Rate { get; init; }
    public string Direction { get; init; } = "up";
}

public class MotorController
{
    private readonly object syncLock = new();
    private readonly HistoryData history = new();
    private readonly ManualResetEventSlim pauseGate = new(true);

    private ProjectData? project;
    private CancellationTokenSource operationCts = new();
    private MotorState stateBeforePause = MotorState.Idle;
    private string currentOperation = "idle";
    private JogResumeCommand? pausedJogCommand;
    private string currentStep = "Step: idle";

    // FIX 1: Tunable acceleration ramp time (seconds).
    // This is the time the stepper spends accelerating from rest to target speed
    // (and decelerating back to rest). Validation data showed ~0.25s overhead per
    // move at moderate strains. Tune this to match your driver's actual ramp config.
    // Total ramp overhead per move = 2 * RampTimeSeconds (accel + decel).
    private const float RampTimeSeconds = 0.125f;

    // FIX 2: How long to poll after a hardware move completes before declaring
    // the position settled. This lets the Python side's final encoder read arrive.
    private const int SettleDelayMs = 50;

    // FIX 3: Minimum position change (mm) to consider an encoder update "real"
    // vs. noise. Derived from step size: 0.003048 mm/microstep.
    private const float PositionEpsilon = 0.002f;

    public int MotorID { get; }
    public string MotorName => $"Motor {MotorID + 1}";
    public float motorPosition { get; private set; }
    public MotorState State { get; private set; } = MotorState.Idle;
    public string CurrentStep => currentStep;
    public bool IsBusy => State is MotorState.Moving or MotorState.Jogging or MotorState.Running or MotorState.Paused;
    public bool HasLoadedProject => project is not null;

    //private readonly PythonMotorClient _hardware = new();

    public MotorController(int id)
    {
        MotorID = id;
    }

    public void PublishStatusSnapshot()
    {
        PushState();
        PushPosition();
        SetStep(currentStep, force: true);
    }

    public void CreateProject(List<ProjectAction> actions)
    {
        project = new ProjectData(new ReactorSettings(1, 1));
        project.actionList.AddRange(actions);
        SetState(MotorState.Ready);
        SetStep($"Step: loaded {actions.Count} step(s)");
        PushLog($"[PROGRAM LOAD] {MotorName} loaded {actions.Count} step(s)");
    }

    public async Task Start()
    {
        if (project is null)
        {
            SetState(MotorState.Error);
            PushLog($"[PROGRAM ERROR] {MotorName} has no loaded project");
            throw new InvalidOperationException($"{MotorName} has no project loaded");
        }

        lock (syncLock)
        {
            if (IsBusy)
            {
                throw new InvalidOperationException($"{MotorName} is already busy");
            }

            operationCts = new CancellationTokenSource();
            pauseGate.Set();
            currentOperation = "program";
            pausedJogCommand = null;
        }

        SetState(MotorState.Running);
        PushLog($"[RUN START] {MotorName} loaded {project.actionList.Count} action step(s)");

        try
        {
            for (int index = 0; index < project.actionList.Count; index++)
            {
                var action = project.actionList[index];
                await WaitWhilePausedAsync(operationCts.Token);
                operationCts.Token.ThrowIfCancellationRequested();

                SetStep($"Step: {index + 1}/{project.actionList.Count} {action.Describe()}");
                PushLog($"[RUN] {MotorName} step {index + 1}: {action.Describe()}");

                await action.PerformAction(this, operationCts.Token);
                await history.RecordActionAsync(MotorID, action.ActionType);
            }

            SetStep("Step: complete");
            PushLog($"[RUN COMPLETE] {MotorName}");
        }
        catch (OperationCanceledException)
        {
            SetStep("Step: stopped");
            PushLog($"[RUN STOPPED] {MotorName}");
        }
        catch (Exception ex)
        {
            SetState(MotorState.Error);
            SetStep("Step: error");
            PushLog($"[RUN ERROR] {MotorName}: {ex.Message}");
        }
        finally
        {
            lock (syncLock)
            {
                currentOperation = "idle";
                pausedJogCommand = null;
            }

            pauseGate.Set();

            if (State != MotorState.Error)
            {
                SetState(MotorState.Idle);
                _ = ResetStepLaterAsync();
            }
        }
    }

    public async Task MoveAbsolute(float targetPosition, float rate = 1.0f)
    {
        lock (syncLock)
        {
            if (IsBusy)
            {
                throw new InvalidOperationException($"{MotorName} is already busy");
            }

            operationCts = new CancellationTokenSource();
            pauseGate.Set();
            currentOperation = "manual_move";
            pausedJogCommand = null;
        }

        SetState(MotorState.Moving);
        SetStep($"Step: moving to {targetPosition:0.###} mm");
        PushLog($"[MOVE START] {MotorName} absolute -> {targetPosition:0.###} mm");

        try
        {
            await RunHardwareMoveAsync(targetPosition, rate, operationCts.Token);
            PushLog($"[MOVE END] {MotorName} pos={motorPosition:0.###}");
        }
        catch (OperationCanceledException)
        {
            PushLog($"[MOVE STOPPED] {MotorName}");
        }
        catch (Exception ex)
        {
            SetState(MotorState.Error);
            SetStep("Step: error");
            PushLog($"[MOVE ERROR] {MotorName}: {ex.Message}");
        }
        finally
        {
            lock (syncLock)
            {
                currentOperation = "idle";
            }

            pauseGate.Set();

            if (State != MotorState.Error)
            {
                SetState(MotorState.Idle);
                _ = ResetStepLaterAsync();
            }
        }
    }

    public Task MoveRelative(float distance, float rate = 1.0f)
    {
        var currentPosition = motorPosition;
        return MoveAbsolute(currentPosition + distance, rate);
    }

    public Task JogStart(float rate, int direction)
    {
        var normalizedDirection = direction >= 0 ? 1 : -1;
        var directionText = normalizedDirection > 0 ? "up" : "down";

        lock (syncLock)
        {
            if (IsBusy)
            {
                throw new InvalidOperationException($"{MotorName} is already busy");
            }

            operationCts = new CancellationTokenSource();
            pauseGate.Set();
            currentOperation = "jog";
            pausedJogCommand = new JogResumeCommand
            {
                Motor = MotorName,
                Rate = Math.Abs(rate),
                Direction = directionText
            };
        }

        SetState(MotorState.Jogging);
        SetStep($"Step: jogging {directionText} at {Math.Abs(rate):0.###} mm/s");
        PushLog($"[JOG START] {MotorName} dir={directionText} rate={Math.Abs(rate):0.###}");

        _ = Task.Run(async () =>
        {
            var token = operationCts.Token;
            var lastTick = DateTime.UtcNow;

            try
            {
                while (true)
                {
                    await WaitWhilePausedAsync(token);
                    token.ThrowIfCancellationRequested();

                    var now = DateTime.UtcNow;
                    var deltaSeconds = (float)(now - lastTick).TotalSeconds;
                    lastTick = now;

                    if (deltaSeconds <= 0)
                    {
                        deltaSeconds = 0.05f;
                    }

                    // FIX: Jog still uses dead-reckoning because the hardware is
                    // continuously moving and there is no discrete target to poll against.
                    // This is acceptable — jog is a manual positioning aid, not a
                    // precision motion. The position is snapped from real encoder data
                    // the next time a non-jog move or program step runs.
                    UpdatePosition(motorPosition + (Math.Abs(rate) * normalizedDirection * deltaSeconds));
                    await Task.Delay(50, token);
                }
            }
            catch (OperationCanceledException)
            {
                PushLog($"[JOG STOP] {MotorName}");
            }
            catch (Exception ex)
            {
                SetState(MotorState.Error);
                SetStep("Step: error");
                PushLog($"[JOG ERROR] {MotorName}: {ex.Message}");
            }
            finally
            {
                lock (syncLock)
                {
                    currentOperation = "idle";
                    pausedJogCommand = null;
                }

                pauseGate.Set();

                if (State != MotorState.Error)
                {
                    SetState(MotorState.Idle);
                    _ = ResetStepLaterAsync();
                }
            }
        });

        return Task.CompletedTask;
    }

    public void JogStop()
    {
        EmergencyStop();
    }

    public void Pause()
    {
        lock (syncLock)
        {
            if (State == MotorState.Running || State == MotorState.Jogging)
            {
                stateBeforePause = State;
                pauseGate.Reset();
                SetState(MotorState.Paused);
                SetStep($"Step: paused ({currentOperation})");
                PushLog($"[PAUSE] {MotorName} paused");
                return;
            }
        }

        if (State == MotorState.Moving)
        {
            PushLog($"[PAUSE] {MotorName} stopping manual move; resume is unavailable for in-flight manual moves");
            EmergencyStop();
        }
    }

    public JogResumeCommand? Resume()
    {
        lock (syncLock)
        {
            if (State != MotorState.Paused)
            {
                return null;
            }

            pauseGate.Set();
            SetState(stateBeforePause);
            PushLog($"[RESUME] {MotorName} resumed");

            if (currentOperation == "program")
            {
                return null;
            }

            if (currentOperation == "jog")
            {
                SetStep($"Step: jogging {pausedJogCommand?.Direction ?? "up"} at {pausedJogCommand?.Rate ?? 0:0.###} mm/s");
                return pausedJogCommand;
            }

            return null;
        }
    }

    public void EmergencyStop()
    {
        lock (syncLock)
        {
            pauseGate.Set();
            operationCts.Cancel();
        }
    }

    // ---------------------------------------------------------------------------
    // FIX: RunHardwareMoveAsync replaces RunInterpolatedMoveAsync.
    //
    // OLD approach: issue hardware command once, then fake the position by
    // linearly interpolating over an estimated duration. This caused the UI to
    // show the "right" position before the motor got there (or after), and the
    // error compounded over cycles because ramp time was not accounted for.
    //
    // NEW approach:
    //   1. Calculate a realistic expected duration including ramp time.
    //   2. Issue the hardware command.
    //   3. Poll the real encoder position from Python at 50 ms intervals.
    //   4. Only update the UI when the encoder reports a meaningfully different
    //      position (> PositionEpsilon), so noise doesn't cause false updates.
    //   5. After the expected duration, allow a settle window for the final
    //      encoder read to arrive before snapping to the exact target.
    // ---------------------------------------------------------------------------
    public async Task RunHardwareMoveAsync(
        float targetPosition,
        float rate,
        CancellationToken token,
        float? forcedDurationSeconds = null)
    {
        var startPos = motorPosition;
        var distance = Math.Abs(targetPosition - startPos);
        var speed = Math.Max(Math.Abs(rate), 0.1f);

        // FIX: Add 2× ramp time (accel + decel) to the raw distance/speed estimate.
        // This is the core correction for the time-accuracy errors seen in validation.
        var estimatedDurationSeconds = forcedDurationSeconds
            ?? Math.Max(0.15f, (distance / speed) + (2 * RampTimeSeconds));

        // Issue the hardware command once. Python handles all pulse timing.
        await Program.Python.MoveAbsolute(MotorName, targetPosition, rate);

        // Poll real encoder position until the estimated duration has elapsed.
        var deadline = DateTime.UtcNow.AddSeconds(estimatedDurationSeconds);

        while (DateTime.UtcNow < deadline)
        {
            await WaitWhilePausedAsync(token);
            token.ThrowIfCancellationRequested();

            // Read actual encoder position from Python hardware layer.
            float encoderPosition = await Program.Python.GetPosition(MotorName);

            // Only push an update if the encoder moved enough to be meaningful.
            if (Math.Abs(encoderPosition - motorPosition) > PositionEpsilon)
            {
                UpdatePosition(encoderPosition);
            }

            await Task.Delay(50, token);
        }

        // Settle window: let the final encoder read arrive after motion stops.
        await Task.Delay(SettleDelayMs, token);

        // Final authoritative read — snap UI to exact encoder position.
        float finalPosition = await Program.Python.GetPosition(MotorName);
        UpdatePosition(finalPosition);

        // Log if we ended up meaningfully far from the target — useful for
        // diagnosing missed steps or mechanical backlash.
        var finalError = Math.Abs(finalPosition - targetPosition);
        if (finalError > PositionEpsilon * 10)
        {
            PushLog($"[POSITION WARN] {MotorName} target={targetPosition:0.###} actual={finalPosition:0.###} err={finalError:0.###} mm");
        }
    }

    // ---------------------------------------------------------------------------
    // Kept for any callers that may reference it (e.g. action types that pass a
    // forcedDurationSeconds for timed holds). Internally delegates to the fixed
    // hardware-polling version.
    // ---------------------------------------------------------------------------
    public Task RunInterpolatedMoveAsync(
        float targetPosition,
        float rate,
        CancellationToken token,
        float? forcedDurationSeconds = null)
    {
        return RunHardwareMoveAsync(targetPosition, rate, token, forcedDurationSeconds);
    }

    public async Task HoldPositionAsync(float seconds, CancellationToken token)
    {
        if (seconds <= 0)
        {
            return;
        }

        var remainingMs = (int)Math.Round(seconds * 1000.0);
        while (remainingMs > 0)
        {
            await WaitWhilePausedAsync(token);
            token.ThrowIfCancellationRequested();

            var slice = Math.Min(remainingMs, 100);
            await Task.Delay(slice, token);
            remainingMs -= slice;
        }
    }

    private async Task WaitWhilePausedAsync(CancellationToken token)
    {
        while (!pauseGate.IsSet)
        {
            token.ThrowIfCancellationRequested();
            await Task.Delay(50, token);
        }
    }

    private async Task ResetStepLaterAsync()
    {
        await Task.Delay(1200);

        if (!IsBusy && State != MotorState.Error)
        {
            SetStep("Step: idle");
        }
    }

    private void UpdatePosition(float position)
    {
        motorPosition = position;
        PushPosition();
    }

    private void PushPosition()
    {
        Program.Backend.PushEvent(new BioreactorEvent
        {
            Type = "motor_position",
            Motor = MotorName,
            Position = motorPosition
        });
    }

    private void PushState()
    {
        Program.Backend.PushEvent(new BioreactorEvent
        {
            Type = "motor_state",
            Motor = MotorName,
            State = State.ToString().ToLowerInvariant()
        });
    }

    private void SetState(MotorState newState)
    {
        if (State == newState)
        {
            return;
        }

        State = newState;
        Console.WriteLine($"{MotorName} State -> {newState}");
        PushState();
    }

    private void SetStep(string step, bool force = false)
    {
        if (!force && currentStep == step)
        {
            return;
        }

        currentStep = step;
        Program.Backend.PushStep(MotorName, step);
    }

    private void PushLog(string message)
    {
        Program.Backend.PushLog(MotorName, message);
    }
}

public static class MotorThread
{
    public static async Task RunMotor(MotorController motor, ProjectData project, HistoryData history)
    {
        Console.WriteLine($"{motor.MotorName} starting execution");

        foreach (var action in project.actionList)
        {
            try
            {
                await action.PerformAction(motor, CancellationToken.None);
                await history.RecordActionAsync(motor.MotorID, action.ActionType);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"{motor.MotorName} encountered an error: {ex.Message}");
            }
        }

        Console.WriteLine($"{motor.MotorName} finished execution");
    }
}
