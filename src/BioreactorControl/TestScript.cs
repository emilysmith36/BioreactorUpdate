using System.Threading.Tasks;

class BioreactorTest
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Starting Test Script");

        // Setup reactor and project
        ReactorSettings reactor = new ReactorSettings(1, 3);
        ProjectData project = new ProjectData(reactor);

        // Add actions here
        var loop = new LoopAction(3);
        loop.AddAction(new ManualAction(100, 10));
        loop.AddAction(new WaitAction(2));
        loop.AddAction(new ManualAction(0, 10));

        project.actionList.Add(new ManualAction(100, 10));
        project.actionList.Add(new WaitAction(3));
        project.actionList.Add(loop);
        project.actionList.Add(new ManualAction(200, 20));

        // Start backend with this project
        BackendManagement backend = new BackendManagement();
        await backend.Initialize(project);
        await backend.StartProject();
    }
}