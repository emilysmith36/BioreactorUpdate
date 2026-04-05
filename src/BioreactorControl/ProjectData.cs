namespace BioreactorControl.Projects;

using BioreactorControl.Motors;

/* ---------------- PROJECT DATA ---------------- */

public class ProjectData
{
    public ReactorSettings reactorSettings { get; set; }
    public int projectID { get; set; }
    public List<ProjectAction> actionList { get; set; }

    public ProjectData(ReactorSettings reactor)
    {
        reactorSettings = reactor;
        projectID = 1;
        actionList = new List<ProjectAction>(); // empty list, to be filled externally
    }
}



/* ---------------- REACTOR SETTINGS ---------------- */

public class ReactorSettings
{
    public int reactorConnectionID { get; set; }

    public int numberOfMotors { get; set; }

    public ReactorSettings(int id, int motors)
    {
        reactorConnectionID = id;
        numberOfMotors = motors;
    }
}


/* Project ACtions: */

/* ---------------- BASE ACTION ---------------- */
public abstract class ProjectAction
{
    public string ActionType { get; set; }

    protected ProjectAction(string type)
    {
        ActionType = type;
    }

    // PerformAction now accepts MotorController for state & cancellation
    public virtual async Task PerformAction(MotorController motor)
    {
        if (motor.State != MotorState.Running)
        {
            Console.WriteLine($"Motor {motor.MotorID} is not running. Skipping {ActionType}.");
            return;
        }

        Console.WriteLine($"Motor {motor.MotorID}: Performing {ActionType} (base)");
        await Task.Delay(500); // placeholder
    }
}

/* ---------------- MANUAL ACTION ---------------- */
public class ManualAction : ProjectAction
{
    public int Position { get; set; }
    public int Rate { get; set; }

    public ManualAction(int position, int rate) 
        : base("Manual Action")
    {
        Position = position;
        Rate = rate;
    }

    public override async Task PerformAction(MotorController motor)
    {
        if (motor.State != MotorState.Running)
        {
            Console.WriteLine($"Motor {motor.MotorID} is not running. Skipping ManualAction.");
            return;
        }

        Console.WriteLine($"Motor {motor.MotorID}: Moving to {Position} at rate {Rate}");
        await Task.Delay(1000); // simulate motion
        motor.motorPosition = Position;
    }
}

/* ---------------- WAIT ACTION ---------------- */
public class WaitAction : ProjectAction
{
    public int WaitSeconds { get; set; }

    public WaitAction(int seconds) 
        : base("Wait Action")
    {
        WaitSeconds = seconds;
    }

    public override async Task PerformAction(MotorController motor)
    {
        if (motor.State != MotorState.Running)
        {
            Console.WriteLine($"Motor {motor.MotorID} is not running. Skipping WaitAction.");
            return;
        }

        Console.WriteLine($"Motor {motor.MotorID}: Waiting for {WaitSeconds} seconds");
        await Task.Delay(WaitSeconds * 1000);
        Console.WriteLine($"Motor {motor.MotorID}: Finished waiting");
    }
}

/* ---------------- LOOP ACTION ---------------- */
public class LoopAction : ProjectAction
{
    private readonly List<ProjectAction> loopActions = new();

    public int LoopCount { get; set; }

    public LoopAction(int count) 
        : base("Loop Action")
    {
        LoopCount = count;
    }

    public void AddAction(ProjectAction action) => loopActions.Add(action);
    public void RemoveAction(ProjectAction action) => loopActions.Remove(action);
    public IReadOnlyList<ProjectAction> GetActions() => loopActions.AsReadOnly();

    public override async Task PerformAction(MotorController motor)
    {
        if (motor.State != MotorState.Running)
        {
            Console.WriteLine($"Motor {motor.MotorID} is not running. Skipping LoopAction.");
            return;
        }

        Console.WriteLine($"Motor {motor.MotorID}: Starting loop ({LoopCount} iterations)");

        for (int i = 0; i < LoopCount; i++)
        {
            Console.WriteLine($"Motor {motor.MotorID}: Loop iteration {i + 1}");
            foreach (var action in loopActions)
            {
                if (motor.State != MotorState.Running)
                {
                    Console.WriteLine($"Motor {motor.MotorID}: Loop stopped early due to state {motor.State}");
                    return;
                }

                await action.PerformAction(motor);
            }
        }

        Console.WriteLine($"Motor {motor.MotorID}: Finished loop");
    }
}
