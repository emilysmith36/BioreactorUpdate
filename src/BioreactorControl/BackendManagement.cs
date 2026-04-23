namespace BioreactorControl.Backend;

using System.Collections.Concurrent;
using BioreactorControl.Motors;
using BioreactorControl.Projects;

public class BioreactorEvent
{
    public string Type { get; set; } = string.Empty;
    public string Motor { get; set; } = string.Empty;
    public object? Message { get; set; }
    public float Position { get; set; }
    public string State { get; set; } = string.Empty;
    public string Step { get; set; } = string.Empty;
}

public class BackendManagement
{
    public List<MotorController> Motors { get; } = new();
    private readonly ConcurrentQueue<BioreactorEvent> eventQueue = new();

    public Task Initialize()
    {
        const int numberOfMotors = 3;

        for (int i = 0; i < numberOfMotors; i++)
        {
            var motor = new MotorController(i);
            Motors.Add(motor);
            motor.PublishStatusSnapshot();
        }

        return Task.CompletedTask;
    }

    public bool TryGetMotor(string motorName, out MotorController? motor)
    {
        motor = Motors.FirstOrDefault(m => string.Equals(m.MotorName, motorName, StringComparison.OrdinalIgnoreCase));
        return motor is not null;
    }

    public void EmergencyStopAll()
    {
        foreach (var motor in Motors)
        {
            motor.EmergencyStop();
        }
    }

    public void PauseAll()
    {
        foreach (var motor in Motors)
        {
            motor.Pause();
        }
    }

    public List<JogResumeCommand> ResumeAll()
    {
        var commands = new List<JogResumeCommand>();

        foreach (var motor in Motors)
        {
            var command = motor.Resume();
            if (command is not null)
            {
                commands.Add(command);
            }
        }

        return commands;
    }

    public void PushEvent(BioreactorEvent ev) => eventQueue.Enqueue(ev);

    public void PushLog(string motor, string message)
    {
        PushEvent(new BioreactorEvent
        {
            Type = "log",
            Motor = motor,
            Message = message
        });
    }

    public void PushStep(string motor, string step)
    {
        PushEvent(new BioreactorEvent
        {
            Type = "motor_step",
            Motor = motor,
            Step = step
        });
    }

    public List<BioreactorEvent> DequeueEvents()
    {
        var events = new List<BioreactorEvent>();
        while (eventQueue.TryDequeue(out var ev))
        {
            events.Add(ev);
        }

        return events;
    }
}

public class ProgramLoadRequest
{
    public string Motor { get; set; } = string.Empty;
    public List<StepPayload> Steps { get; set; } = new();
}

public class StepPayload
{
    public string type { get; set; } = string.Empty;
    public string direction { get; set; } = string.Empty;
    public float rate { get; set; }
    public float frequency_hz { get; set; }
    public float displacement_mm { get; set; }
    public string timing_mode { get; set; } = string.Empty;
    public float duration_seconds { get; set; }
    public float estimated_seconds { get; set; }
    public int cycles { get; set; }
    public float target_position_mm { get; set; }
    public string label { get; set; } = string.Empty;
}

public class JogRequest
{
    public string Motor { get; set; } = string.Empty;
    public float Rate { get; set; }
    public string Direction { get; set; } = string.Empty;
}

public class HistoryData
{
    private readonly ConcurrentQueue<string> historyLog = new();
    private readonly SemaphoreSlim logLock = new(1, 1);

    public async Task RecordActionAsync(int motorID, string action)
    {
        await logLock.WaitAsync();

        try
        {
            var log = $"Motor {motorID + 1} executed {action}";
            historyLog.Enqueue(log);
            Console.WriteLine($"History Logged: {log}");
        }
        finally
        {
            logLock.Release();
        }
    }

    public void PrintHistory()
    {
        Console.WriteLine("\n---- ACTION HISTORY ----");
        foreach (var entry in historyLog)
        {
            Console.WriteLine(entry);
        }
    }
}
