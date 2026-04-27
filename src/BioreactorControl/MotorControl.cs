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
            await RunInterpolatedMoveAsync(targetPosition, rate, operationCts.Token);
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

    public async Task RunInterpolatedMoveAsync(
        float targetPosition,
        float rate,
        CancellationToken token,
        float? forcedDurationSeconds = null)
    {
        // --- ADD THIS LINE: Tell the hardware to start moving ---
        // We call this once at the start. The Python side handles the pulse timing.
        await Program.Python.MoveAbsolute(MotorName, targetPosition, rate);

        var startPos = motorPosition;
        var distance = targetPosition - startPos;
        var speed = Math.Max(Math.Abs(rate), 0.1f);
        var durationSeconds = forcedDurationSeconds ?? Math.Max(0.15f, Math.Abs(distance) / speed);
        
        // The rest of this method updates the UI "progress bar" / position display
        var stepCount = Math.Max(1, (int)Math.Ceiling(durationSeconds / 0.05f));
        var delayMs = Math.Max(10, (int)Math.Round((durationSeconds / stepCount) * 1000.0));

        for (int i = 1; i <= stepCount; i++)
        {
            await WaitWhilePausedAsync(token);
            token.ThrowIfCancellationRequested();

            var nextPosition = startPos + (distance * (i / (float)stepCount));
            UpdatePosition(nextPosition);

            if (i < stepCount)
            {
                await Task.Delay(delayMs, token);
            }
        }

        await Task.Delay(10, token);

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
