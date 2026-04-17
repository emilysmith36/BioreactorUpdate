//MotorControl.cs
namespace BioreactorControl.Motors;

using BioreactorControl.Backend;
using BioreactorControl.Projects;

public enum MotorState
{
    Idle,
    WaitingForProject,
    Ready,
    Running,
    Stopped,
    Error
}

/*public class MotorData
{
    public int motorID { get; set; }

    public float motorPosition { get; set; }

    public bool connected { get; set; }

    public MotorData(int id)
    {
        motorID = id;
        motorPosition = 0;
        connected = true;
    }
}*/

public class MotorController
{
    public int MotorID { get; }

    public float motorPosition { get; set; }

    //public MotorData motorData { get; set; }

    private ProjectData? project;
    private HistoryData history = new();

    private CancellationTokenSource cts = new();

    public MotorState State { get; private set; } = MotorState.Idle;

    public MotorController(int id)
    {
        MotorID = id;
        motorPosition = 0; // Needs to be updated based on actual position from hardware
        //motorData = new MotorData(id);
    }

    private void SetState(MotorState newState)
    {
        // ONLY act if the state is actually different
        if (this.State == newState) return;

        this.State = newState;
        Console.WriteLine($"Motor {MotorID} State -> {newState}");

        // Tell the frontend what's up, yo:
        Program.Backend.PushEvent(new BioreactorEvent {
            Type = "motor_state",
            Motor = $"Motor {MotorID + 1}",
            State = newState.ToString().ToLower() 
        });
    }

    // 🔹 Placeholder for UI/API project creation
    public async Task CreateProjectAsync()
    {
        SetState(MotorState.WaitingForProject);

        await Task.Delay(1000); // simulate delay

        try
        {
            var proj = new ProjectData(new ReactorSettings(1, 1));

            var loop = new LoopAction(2);
            loop.AddAction(new ManualAction(50, 5));
            loop.AddAction(new WaitAction(1));

            proj.actionList.Add(new ManualAction(100, 10));
            proj.actionList.Add(loop);

            project = proj;

            SetState(MotorState.Ready);
        }
        catch
        {
            SetState(MotorState.Error);
        }
    }

    // Create a project with a specific action list
    public void CreateProject(List<ProjectAction> actions)
    {
        var proj = new ProjectData(new ReactorSettings(1, 1));
        proj.actionList.AddRange(actions);
        project = proj;
        SetState(MotorState.Ready);
    }

    public async Task Start()
    {
        if (project == null)
        {
            SetState(MotorState.Error);
            throw new InvalidOperationException($"Motor {MotorID} has no project");
        }

        if (State != MotorState.Ready && State != MotorState.Stopped)
        {
            Console.WriteLine($"Motor {MotorID} cannot start from state {State}");
            return;
        }

        cts = new CancellationTokenSource(); // reset token
        SetState(MotorState.Running);

        try
        {
            foreach (var action in project.actionList)
            {
                cts.Token.ThrowIfCancellationRequested();

                await action.PerformAction(this);

                await history.RecordActionAsync(MotorID, action.ActionType);
            }

            SetState(MotorState.Stopped);
            Console.WriteLine($"Motor {MotorID}: Project complete");
        }
        catch (OperationCanceledException)
        {
            SetState(MotorState.Stopped);
            Console.WriteLine($"Motor {MotorID}: Emergency stopped");
        }
        catch (Exception ex)
        {
            SetState(MotorState.Error);
            Console.WriteLine($"Motor {MotorID}: ERROR - {ex.Message}");
        }
    }

    public void EmergencyStop()
    {
        if (State == MotorState.Running)
        {
            Console.WriteLine($"Motor {MotorID}: EMERGENCY STOP");
            cts.Cancel();
        }
    }

    public async Task MoveAbsolute(float targetPosition)
    {
        SetState(MotorState.Running);
        float startPos = this.motorPosition;
        float distance = targetPosition - startPos;
        
        // Simulate movement over 1 second
        int steps = 10;
        for (int i = 1; i <= steps; i++)
        {
            this.motorPosition = startPos + (distance * (i / (float)steps));
            
            // Push the new position to the UI
            Program.Backend.PushEvent(new BioreactorEvent {
                Type = "motor_position",
                Motor = $"Motor {MotorID + 1}",
                Position = this.motorPosition
            });
            
            await Task.Delay(100);
        }

        SetState(MotorState.Idle);
        Console.WriteLine($"Motor {MotorID} moved to absolute position: {targetPosition}");
    }

    public async Task MoveRelative(float distance)
    {
        await MoveAbsolute(this.motorPosition + distance);
    }

    //demo
    public async Task JogStart(float rate, int direction, int motor)
    {
        State = MotorState.Running;

        await Task.Run(async () =>
        {
            while (State == MotorState.Running)
            {
                float difference = rate * direction * 0.01f;
                motorPosition += delta;

                Backend.PushEvent(new BioreactorEvent
                {
                    Type = "jog_start",
                    Motor = motorNum.toString(),
                    Message = "Motor jog started",
                    Position = null,
                    State = "running",
                    Step = null,
                });

                await Task.Delay(10);
            }
        });
    }

    //demo
    public async JogStop()
    {
        State = MotorState.Idle;
    }

}

/* ---------------- MOTOR THREAD (ASYNC WORKER) ---------------- */

public static class MotorThread
{
    public static async Task RunMotor(MotorController motor, ProjectData project, HistoryData history)
    {
        Console.WriteLine($"Motor {motor.MotorID} starting execution");

        // Copy the action list at the start to allow UI modifications before starting
        var actionsToRun = new List<ProjectAction>(project.actionList);

        foreach (var action in actionsToRun)
        {
            try
            {
                await action.PerformAction(motor);

                await history.RecordActionAsync(motor.MotorID, action.ActionType);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Motor {motor.MotorID} encountered an error: {ex.Message}");
            }
        }

        Console.WriteLine($"Motor {motor.MotorID} finished execution");
    }
}

