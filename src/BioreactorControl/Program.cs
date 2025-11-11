// See https://aka.ms/new-console-template for more information

using System.Buffers;
using System.IO.Compression;
using System.Runtime.InteropServices;

Console.WriteLine("Hello, World!");
Console.WriteLine("Starting Project");
var reactorData = new ReactorSettings(1, 1);
var projectData = new ProjectSettings( reactorData );
var executionManager = new ExecutionManagement( projectData );
executionManager.Initialize();
executionManager.executeProject();

public class ExecutionManagement
{

    private ReactorSettings reactorSettings;
    private ProjectSettings projectSettings;

    private bool motorListInitialized;
    public List<MotorThread> motorList { get; set; }

    public ExecutionManagement(ProjectSettings projectData)
    {
        projectSettings = projectData;
        reactorSettings = projectSettings.reactorSettings;
    }

    public void Initialize()
    {
        Console.WriteLine("Starting Execution Manager");
        InitializeReactor();
    }

    private void InitializeReactor()
    {
        Console.WriteLine("Connecting To Reactor");
        Console.WriteLine($"Reactor ID: {reactorSettings.reactorConnectionID}");
        Console.WriteLine($"Number of Motors: {reactorSettings.numberOfMotors}");
        motorListInitialized = false;
        motorList = [];
        Console.WriteLine("Reactor Connection Sucessful");
    }

    public void executeProject()
    {
        Console.WriteLine($"Executing Project of ID: {projectSettings.projectID}");
        initializeMotorList();
        printMotorList();
    }

    public void initializeMotorList()
    {
        for (int i = 0; i < reactorSettings.numberOfMotors; i++)
        {
            motorList.Add(new MotorThread(i));
        }
        motorListInitialized = true;
    }

    public void printMotorList()
    {
        if (motorListInitialized)
        {
            for (int i = 0; i < reactorSettings.numberOfMotors; i++)
            {
                motorList[i].printMotorData();
            }
        }
        else
        {
            Console.WriteLine("Error: Motor List not initialized and unable to be printed.");
        }
    }

}

public class ReactorSettings
{
    public int reactorConnectionID { get; set; }
    public int numberOfMotors { get; set; }

    public ReactorSettings (int connectionID, int motorsCount)
    {
        reactorConnectionID = connectionID;
        numberOfMotors = motorsCount;
    }

}

public class ProjectSettings
{
    public ReactorSettings reactorSettings { get; set; }
    public int projectID { get; set; }

    public ProjectSettings ( ReactorSettings reactor )
    {
        reactorSettings = reactor;
        projectID = 0;
    }

}

public class MotorThread
{
    private int motorID { get; set; }
    private bool connected { get; set; }

    public MotorThread(int id)
    {
        motorID = id;
        connected = true;
    }

    public void printMotorData()
    {
        Console.WriteLine($"Printing Data for Motor of ID: {motorID} Connected?: {connected}");
    }
}
