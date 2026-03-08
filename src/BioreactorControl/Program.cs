using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

Console.WriteLine("Starting Backend");

BackendManagement backend = new BackendManagement();
await backend.Initialize();
await backend.StartProject();



/* ---------------- BACKEND MANAGEMENT ---------------- */

public class BackendManagement
{
    private ExecutionManagement executionManager;
    private HistoryData history;

    public async Task Initialize()
    {
        Console.WriteLine("Backend Manager Starting");

        history = new HistoryData();

        ReactorSettings reactor = new ReactorSettings(1, 3);
        ProjectData project = new ProjectData(reactor);

        executionManager = new ExecutionManagement(project, history);

        await executionManager.Initialize();
    }

    public async Task StartProject()
    {
        await executionManager.ExecuteProject();
    }
}



/* ---------------- EXECUTION MANAGEMENT ---------------- */

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

        // Building Example Action lists:
        var loop = new LoopAction(3);
        loop.AddAction(new ManualAction(100, 10));
        loop.AddAction(new WaitAction(2));
        loop.AddAction(new ManualAction(0, 10));
        actionList = new List<ProjectAction>
        {
            new ManualAction(100,10),
            new WaitAction(3),
            loop,
            new ManualAction(200,20)
        };
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



/* ---------------- MOTOR DATA ---------------- */

public class MotorData
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
}



/* ---------------- MOTOR THREAD (ASYNC WORKER) ---------------- */

public static class MotorThread
{
    public static async Task RunMotor(
        MotorData motor,
        ProjectData project,
        HistoryData history)
    {
        Console.WriteLine($"Motor {motor.motorID} starting execution");

        foreach (var action in project.actionList)
        {
            await action.PerformAction(motor);

            history.RecordAction(motor.motorID, action.actionType);
        }

        Console.WriteLine($"Motor {motor.motorID} finished execution");
    }
}



/* ---------------- THREAD SAFE HISTORY ---------------- */

public class HistoryData
{
    private ConcurrentQueue<string> historyLog = new();

    private SemaphoreSlim logLock = new(1,1);

    public async void RecordAction(int motorID, string action)
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



/* Project ACtions: */

public class ProjectAction
{
    public string actionType { get; set; }

    public virtual async Task PerformAction(MotorData motor)
    {
        Console.WriteLine("Performing Base Action");

        await Task.Delay(500);
    }
}

public class ManualAction : ProjectAction
{
    public int position;
    public int rate;

    public ManualAction(int pos, int rateValue)
    {
        actionType = "Manual Action";

        position = pos;
        rate = rateValue;
    }

    public override async Task PerformAction(MotorData motor)
    {
        Console.WriteLine($"Motor {motor.motorID} moving to {position} at rate {rate}");

        await Task.Delay(1000);

        motor.motorPosition = position;
    }
}

public class WaitAction : ProjectAction
{
    public int waitSeconds;

    public WaitAction(int seconds)
    {
        actionType = "Wait Action";
        waitSeconds = seconds;
    }

    public override async Task PerformAction(MotorData motor)
    {
        Console.WriteLine($"Motor {motor.motorID} waiting for {waitSeconds} seconds");

        await Task.Delay(waitSeconds * 1000);

        Console.WriteLine($"Motor {motor.motorID} finished waiting");
    }
}

public class LoopAction : ProjectAction
{
    public int loopCount;
    public List<ProjectAction> loopActions;

    public LoopAction(int count)
    {
        actionType = "Loop Action";
        loopCount = count;
        loopActions = new List<ProjectAction>();
    }

    public void AddAction(ProjectAction action)
    {
        loopActions.Add(action);
    }

    public override async Task PerformAction(MotorData motor)
    {
        Console.WriteLine($"Motor {motor.motorID} starting loop ({loopCount} iterations)");

        for (int i = 0; i < loopCount; i++)
        {
            Console.WriteLine($"Motor {motor.motorID} loop iteration {i + 1}");

            foreach (var action in loopActions)
            {
                await action.PerformAction(motor);
            }
        }

        Console.WriteLine($"Motor {motor.motorID} finished loop");
    }
}