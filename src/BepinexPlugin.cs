using BepInEx;
using BepInEx.Logging;
using BepInEx.Configuration;
using HarmonyLib;
using System;
using System.Reflection;

namespace UsableGlasses;

[BepInPlugin(LCMPluginInfo.PLUGIN_GUID, LCMPluginInfo.PLUGIN_NAME, LCMPluginInfo.PLUGIN_VERSION)]
public class Plugin : BaseUnityPlugin
{
  internal static ManualLogSource Log = null!;

  internal static ConfigEntry<bool> configDebugGeneral = null!;
    private void Awake()
  {
    Log = Logger;

    configDebugGeneral = Config.Bind("General",
                                  "DebugMode",
                                  false,
                                  "Toggles logging more debug information to the console and log file.");

    // Log our awake here so we can see it in LogOutput.txt file
    Log.LogInfo($"Plugin {LCMPluginInfo.PLUGIN_NAME} version {LCMPluginInfo.PLUGIN_VERSION} is loaded!");
    try
    {
      Harmony harmony = new Harmony(LCMPluginInfo.PLUGIN_GUID);
      //Log.LogInfo("Try not to die");

      //dotnet build -p:DeployToProd=true

      // This adds in the patches.
      harmony.PatchAll(typeof(Slots_Patch));

      Log.LogInfo("Successfully initialized Usable Glasses patch");
    }
    catch (Exception ex)
    {
      Log.LogError($"Error while initializing:\n{ex}\n");
    }
  }

 public static void LogDebug(string text)
  {
    if (configDebugGeneral.Value)
      Log.LogDebug(text);
  }
}
