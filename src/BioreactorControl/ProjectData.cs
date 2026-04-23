namespace BioreactorControl.Projects;

using BioreactorControl.Motors;

public class ProjectData
{
    public ReactorSettings reactorSettings { get; set; }
    public int projectID { get; set; }
    public List<ProjectAction> actionList { get; set; }

    public ProjectData(ReactorSettings reactor)
    {
        reactorSettings = reactor;
        projectID = 1;
        actionList = new List<ProjectAction>();
    }
}

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

public abstract class ProjectAction
{
    public string ActionType { get; set; }

    protected ProjectAction(string type)
    {
        ActionType = type;
    }

    public virtual string Describe() => ActionType;

    public virtual async Task PerformAction(MotorController motor, CancellationToken token)
    {
        await motor.HoldPositionAsync(0.5f, token);
    }
}

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

    public override string Describe() => $"manual move to {Position} mm at {Rate} mm/s";

    public override Task PerformAction(MotorController motor, CancellationToken token)
    {
        return motor.RunInterpolatedMoveAsync(Position, Rate, token);
    }
}

public class WaitAction : ProjectAction
{
    public int WaitSeconds { get; set; }

    public WaitAction(int seconds)
        : base("Wait Action")
    {
        WaitSeconds = seconds;
    }

    public override string Describe() => $"wait {WaitSeconds} second(s)";

    public override Task PerformAction(MotorController motor, CancellationToken token)
    {
        return motor.HoldPositionAsync(WaitSeconds, token);
    }
}

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

    public override string Describe() => $"loop {LoopCount} time(s)";

    public override async Task PerformAction(MotorController motor, CancellationToken token)
    {
        for (int i = 0; i < LoopCount; i++)
        {
            foreach (var action in loopActions)
            {
                token.ThrowIfCancellationRequested();
                await action.PerformAction(motor, token);
            }
        }
    }
}

public class CycleBasedAction : ProjectAction
{
    public string Direction { get; set; }
    public float Rate { get; set; }
    public float Frequency { get; set; }
    public float Displacement { get; set; }
    public float DurationSeconds { get; set; }
    public float EstimatedSeconds { get; set; }
    public int Cycles { get; set; }
    public bool UseCycles { get; set; }
    public float TargetPositionMm { get; set; }
    public string Label { get; set; }

    public CycleBasedAction(
        string direction,
        float rate,
        float frequency,
        float displacement,
        float durationSeconds,
        float estimatedSeconds,
        int cycles,
        bool useCycles,
        float targetPositionMm,
        string label)
        : base("Cycle-Based Action")
    {
        Direction = direction;
        Rate = rate;
        Frequency = frequency;
        Displacement = displacement;
        DurationSeconds = durationSeconds;
        EstimatedSeconds = estimatedSeconds;
        Cycles = cycles;
        UseCycles = useCycles;
        TargetPositionMm = targetPositionMm;
        Label = label;
    }

    public override string Describe()
    {
        return string.IsNullOrWhiteSpace(Label)
            ? $"{Direction} displacement={Displacement:0.###} mm"
            : Label;
    }

    public override async Task PerformAction(MotorController motor, CancellationToken token)
    {
        var baseline = motor.motorPosition;
        var target = TargetPositionMm != 0
            ? baseline + TargetPositionMm
            : baseline + (Direction.Equals("compression", StringComparison.OrdinalIgnoreCase) ? -Math.Abs(Displacement) : Math.Abs(Displacement));

        var seconds = ResolveTotalDurationSeconds();
        var cycleCount = ResolveCycleCount(seconds);

        if (cycleCount <= 1)
        {
            await motor.RunInterpolatedMoveAsync(target, Rate, token, seconds > 0 ? seconds : null);
            return;
        }

        var secondsPerCycle = Math.Max(0.2f, seconds / cycleCount);
        var halfCycleSeconds = secondsPerCycle / 2f;

        for (int cycleIndex = 0; cycleIndex < cycleCount; cycleIndex++)
        {
            token.ThrowIfCancellationRequested();
            await motor.RunInterpolatedMoveAsync(target, Rate, token, halfCycleSeconds);
            await motor.RunInterpolatedMoveAsync(baseline, Rate, token, halfCycleSeconds);
        }
    }

    private float ResolveTotalDurationSeconds()
    {
        if (EstimatedSeconds > 0)
        {
            return EstimatedSeconds;
        }

        if (DurationSeconds > 0)
        {
            return DurationSeconds;
        }

        if (UseCycles && Cycles > 0 && Frequency > 0)
        {
            return Cycles / Frequency;
        }

        if (Math.Abs(Displacement) > 0 && Rate > 0)
        {
            return Math.Max(0.2f, Math.Abs(Displacement) / Rate);
        }

        return 0.5f;
    }

    private int ResolveCycleCount(float totalSeconds)
    {
        if (UseCycles && Cycles > 0)
        {
            return Cycles;
        }

        if (Frequency > 0 && totalSeconds > 0)
        {
            return Math.Max(1, (int)Math.Round(totalSeconds * Frequency));
        }

        return 1;
    }
}
