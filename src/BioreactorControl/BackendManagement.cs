// BackendManagement.cs
// Manages the backend, and controls all of the components

namespace BioreactorControl.Backend;

using System.Collections.Concurrent;
using BioreactorControl.Motors;
using BioreactorControl.Projects;

public class BackendManagement
{
    private List<MotorController> motors = new();

    public async Task Initialize()
    {
        ReactorSettings reactor = new ReactorSettings(1, 3);

        for (int i = 0; i < reactor.numberOfMotors; i++)
        {
            motors.Add(new MotorController(i));
        }

        await Task.WhenAll(motors.Select(m => m.CreateProjectAsync()));
    }

    public async Task StartAll()
    {
        await Task.WhenAll(motors.Select(m => m.Start()));
    }

    public void EmergencyStopAll()
    {
        foreach (var motor in motors)
        {
            motor.EmergencyStop();
        }
    }
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