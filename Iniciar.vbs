Set WShell = CreateObject("WScript.Shell")
WShell.CurrentDirectory = "C:\Users\lucas.paim\Desktop\processo_triage"
WShell.Run """C:\Users\lucas.paim\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"" app.py", 0, False