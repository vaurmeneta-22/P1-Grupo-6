using System.IO;
using UnityEditor.Android;
using UnityEngine;

// Scoped to generated builds on Windows. Uses the OS's trusted roots instead
// of changing the bundled JDK or disabling HTTPS certificate validation.
public class VRAndroidGradle : IPostGenerateGradleAndroidProject
{
    public int callbackOrder { get { return 1000; } }
    public void OnPostGenerateGradleAndroidProject(string path)
    {
        if(Application.platform!=RuntimePlatform.WindowsEditor) return;
        string properties=Path.Combine(Directory.GetParent(path).FullName,"gradle.properties");
        string text=File.Exists(properties)?File.ReadAllText(properties):"";
        if(!text.Contains("systemProp.javax.net.ssl.trustStoreType="))
            text+="\nsystemProp.javax.net.ssl.trustStoreType=Windows-ROOT\nsystemProp.javax.net.ssl.trustStore=NONE\n";
        File.WriteAllText(properties,text);
        Debug.Log("H1 GRADLE: Windows trusted root store enabled for this generated build.");
    }
}
