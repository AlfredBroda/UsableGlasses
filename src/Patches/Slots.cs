using HarmonyLib;
using UnityEngine;
using System;

using Ostranauts.Inventory;

namespace UsableGlasses;

public class Slots_Patch
{
    /*
     * dotnet build -p:DeployToProd=true
     * 
     * When every inventory is opened, item is added or removed, one of these functions is run. So I added patch that updates the clothing visibility
    */

    [HarmonyPatch(typeof(Slots), nameof(Slots.SlotItem))]
    [HarmonyPostfix]
    public static void SlotItem_Postfix(Slots __instance, bool __result, string __0, CondOwner __1)
    {
        try
        {
            var paperDollMan = CrewSim.inventoryGUI.PaperDollManager;
            // If the item is glasses, we need to add it to the portrait so that they are rendered correctly.
            if (__0 == "head_glasses")
            {
                GlassesHelper.AddGlasses(paperDollMan.coUs, __1);
            }
        }
        catch (Exception ex)
        {
            Plugin.Log.LogInfo($"Exception in patch of bool Slots::SlotItem(string strSlot, CondOwner co):\n{ex}");
        }
    }
    [HarmonyPatch(typeof(Slots), nameof(Slots.UnSlotItem), new Type[] { typeof(string), typeof(CondOwner), typeof(bool) })]
    [HarmonyPostfix]
    public static void UnSlotItem_Postfix(Slots __instance, CondOwner __result, string __0, CondOwner __1, bool __2) { 
        try
        {
            var paperDollMan = CrewSim.inventoryGUI.PaperDollManager;
            // Checks to see if inventory is not visible (aka we are walking around and NPC puts something on) 
            // Or if inventory is open (aka paperDollMan.coUs is not null), then checks to see if current slot change is same as shown paper doll
            if (!GUIInventory.instance.IsInventoryVisible || (GUIInventory.instance.IsInventoryVisible && (__instance.coUs != paperDollMan.coUs)))
            {
                return;
            }
            if (__result == false || __0 == null)
            {
                return;
            }
            // If the item is glasses, we need to remove it from the portrait so that they are rendered correctly.
            if (__0 == "head_glasses")
            {
                GlassesHelper.RemoveGlasses(paperDollMan.coUs);
            }
        }
        catch (Exception ex)
        {
            Plugin.Log.LogInfo($"Exception in patch of void Slots::UnSlotItem(string strSlot, CondOwner co, bool bForce):\n{ex}");
        }
    }
}

internal class GlassesHelper
{
    private static string _noGlasses = "pbaseGlassesA01";
    public static void AddGlasses(CondOwner coUs, CondOwner coSlotted)
    {
        if (coUs.Crew != null && !coUs.IsRobot)
        {
            // Texture2D texture2D = FaceAnim2.GetPNG(coSlotted);
            Plugin.Log.LogInfo($"Adding glasses for '{coUs.strName}' ('{coSlotted.strName}': '{coSlotted.strPortraitImg}')...");
            Plugin.Log.LogDebug($"AddGlasses('{coUs.strName}') Face parts: {string.Join(", ", coUs.Crew.aFaceParts)}");
            
            if (coUs.Crew.aFaceParts.Length < 1)
            {
                Plugin.Log.LogError($"AddGlasses('{coUs.strName}') Face parts array is empty. Not adding glasses.");
                return;
            }

            string portImage = coSlotted.strPortraitImg;
            // The portrait image needs to be located directly in both 'paperdoll/' and 'portrait/' folders to be used for glasses.
            if (portImage.StartsWith("paperdoll/") && portImage.LastIndexOf("/") <= "paperdoll/".Length)
            {
                portImage = portImage.Substring("paperdoll/".Length);
                coUs.Crew.FaceParts[1] = portImage;
            } else {
                Plugin.Log.LogWarning($"AddGlasses('{coUs.strName}') Portrait image '{coSlotted.strPortraitImg}' needs to be located directly in both 'paperdoll/' and have a 'portrait/' counterpart to be used for glasses. Not adding glasses.");
            }
            GUIRenderTargets.Instance.SetFace(coUs, true); 
        }
    }

    public static void RemoveGlasses(CondOwner coUs)
    {
        Plugin.Log.LogInfo($"Removing glasses for '{coUs.strName}'");
        Plugin.Log.LogDebug($"RemoveGlasses('{coUs.strName}') Face parts: {string.Join(", ", coUs.Crew.aFaceParts)}...");

        if (coUs.Crew.aFaceParts.Length < 1)
        {
            Plugin.Log.LogError($"RemoveGlasses('{coUs.strName}') Face parts array is empty. Not removing glasses.");
            return;
        }

        coUs.Crew.aFaceParts[1] = _noGlasses;
        GUIRenderTargets.Instance.SetFace(coUs, true);
    }
}