// BackendManagement.cs
// Manages the backend, and controls all of the components

namespace BioreactorControl.Backend;

// BackendManagement.cs
using System.Collections.Concurrent;
using BioreactorControl.Motors;
using BioreactorControl.Projects;

public class BioreactorEvent {
    // Adding 'null!' or 'string.Empty' resolves the CS8618 warnings
    public string Type { get; set; } = string.Empty; 
    public string Motor { get; set; } = string.Empty;
    public object? Message { get; set; } 
    public float Position { get; set; }
    public string State { get; set; } = string.Empty;
    public string Step { get; set; } = string.Empty;
}

public class BackendManagement
{
    // Make this public so Program.cs can access it
    public List<MotorController> Motors { get; } = new();
    private ConcurrentQueue<BioreactorEvent> eventQueue = new();

    public async Task Initialize()
    {
        // Adjust the number of motors based on your hardware
        int numberOfMotors = 3; 
        for (int i = 0; i < numberOfMotors; i++)
        {
            Motors.Add(new MotorController(i));
        }
        
        // Use the existing CreateProjectAsync logic if needed
        await Task.WhenAll(Motors.Select(m => m.CreateProjectAsync()));
    }

    public void EmergencyStopAll()
    {
        foreach (var motor in Motors)
        {
            motor.EmergencyStop();
        }
    }

    public void PushEvent(BioreactorEvent ev) => eventQueue.Enqueue(ev);

    public List<BioreactorEvent> DequeueEvents() {
        var events = new List<BioreactorEvent>();
        while (eventQueue.TryDequeue(out var ev)) events.Add(ev);
        return events;
    }
}

// Add these classes to your project (e.g., in a new file Models.cs)
public class ProgramLoadRequest {
    public string Motor { get; set; } = string.Empty; // e.g. "Motor 1"
    public List<StepPayload> Steps { get; set; } = new();
}

public class StepPayload {
    public string type { get; set; } = string.Empty;
    public string direction { get; set; } = string.Empty;
    public float rate { get; set; }
    public float frequency_hz { get; set; }
    public float displacement_mm { get; set; }
    public string timing_mode { get; set; } = string.Empty;
    public float duration_seconds { get; set; }
    public int cycles { get; set; }
}

public class JogRequest {
    public string Motor { get; set; } = string.Empty;
    public float Rate { get; set; }
    public string Direction { get; set; } = string.Empty;
}

public class HistoryData
{
    private ConcurrentQueue<string> historyLog = new();
    private SemaphoreSlim logLock = new(1,1);

    public async Task RecordActionAsync(int motorID, string action)
    {
        await logLock.WaitAsync();

        try
        {
            string log = $"Motor {motorID} executed {action}";
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




// Old system, functionality moved to motorcontroller to allow multiple async projects with each motor instead of one project controlling all three
/*

public class ExecutionManagement
{
    private ProjectData projectData;
    private ReactorSettings reactorSettings;
    private HistoryData history;

    private List<MotorData> motorList = new();

    public ExecutionManagement(ProjectData project, HistoryData historyData)
    {
        projectData = project;
        reactorSettings = project.reactorSettings;
        history = historyData;
    }

    public async Task Initialize()
    {
        Console.WriteLine("Execution Manager Starting");

        await ConnectToReactor();
        InitializeMotors();
    }

    private async Task ConnectToReactor()
    {
        Console.WriteLine("Connecting To Reactor...");

        await Task.Delay(500); // simulate hardware connection

        Console.WriteLine($"Reactor ID: {reactorSettings.reactorConnectionID}");
        Console.WriteLine("Connection Successful");
    }

    private void InitializeMotors()
    {
        for (int i = 0; i < reactorSettings.numberOfMotors; i++)
        {
            motorList.Add(new MotorData(i));
        }
    }

    public async Task ExecuteProject()
    {
        Console.WriteLine($"Executing Project {projectData.projectID}");

        List<Task> tasks = new();

        foreach (var motor in motorList)
        {
            tasks.Add(MotorThread.RunMotor(motor, projectData, history));
        }

        await Task.WhenAll(tasks);

        Console.WriteLine("Project Execution Complete");

        history.PrintHistory();
    }
}
*/