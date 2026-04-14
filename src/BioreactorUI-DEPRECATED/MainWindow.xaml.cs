using System.Windows;
using BioreactorUI.Models;

namespace BioreactorUI
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();

            var reactor = new ReactorModel(1, 1);
            var motor = new MotorModel(0);

        }
    }
}