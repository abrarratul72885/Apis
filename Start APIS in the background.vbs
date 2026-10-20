' Starts APIS without a window. Used by "Start APIS when Windows starts".
Set sh = CreateObject("WScript.Shell")
here = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here
On Error Resume Next
rc = sh.Run("cmd /c py -3 server\apis_server.py --no-browser", 0, False)
If Err.Number <> 0 Then sh.Run "cmd /c python server\apis_server.py --no-browser", 0, False
