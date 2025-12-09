using System;
using System.Collections.Generic;
using System.Text;

namespace BioreactorUI.Models
{
    public class ReactorModel
    {
        public int ReactorID { get; set; }
        public int NumberOfMotors { get; set; }
        public bool ConnectionSuccessful { get; set; }

        public ReactorModel(int id, int motorCount)
        {
            ReactorID = id;
            NumberOfMotors = motorCount;
            ConnectionSuccessful = true; // placeholder
        }
    }
}
