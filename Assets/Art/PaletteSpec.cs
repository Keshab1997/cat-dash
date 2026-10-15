using UnityEngine;

namespace CatDash.Art
{
    /// <summary>
    /// Single source of truth for the Cat Dash palette and the cat texture atlas
    /// regions. Values mirror the colours baked by the procedural generators
    /// (<c>tool/blender_cat.py</c>, <c>tool/blender_propset.py</c>, <c>tool/blender_road.py</c>);
    /// if a colour changes in a generator it must change here in the same commit.
    ///
    /// Radius: Agent B (batch CD-B1). Lives in the <c>CatDash.Art</c> assembly next to the
    /// generated FBX files. Agent C's scene generator may reference <c>CatDash.Art</c> from
    /// <c>CatDash.Editor</c>; that one-line asmdef reference change is Captain-owned.
    /// </summary>
    public static class PaletteSpec
    {
        // ---- Cat (Assets/Art/Generated/Cat.fbx, atlas Textures/Cat_1024.png) ----
        public const string FurHex = "#E9953F";
        public const string FurMidHex = "#F0A855";
        public const string FurDarkHex = "#A85A16";
        public const string CreamHex = "#FBEFD9";
        public const string NoseHex = "#E8918F";
        public const string EyeHex = "#2A1C12";
        public const string IrisHex = "#D9A24B";

        // ---- Props ---------------------------------------------------------------
        public const string WoodHex = "#B87E4C";
        public const string WoodDarkHex = "#94562A";
        public const string WoodFrameHex = "#F3EBD9";
        public const string BarrierTealHex = "#57BFB4";
        public const string BarrierOrangeHex = "#E4764A";
        public const string BarrierCreamHex = "#F7EEDD";
        public const string TerracottaHex = "#C4623C";
        public const string LeafHex = "#5FA24A";
        public const string SoilHex = "#4A3524";

        // ---- Road / street -------------------------------------------------------
        public const string AsphaltHex = "#6C6E73";
        public const string LineWhiteHex = "#EDEBE3";
        public const string PavingHex = "#BCB2A4";
        public const string CurbHex = "#CFCBC2";

        // ---- Typed colours (Unity Color is linear; hex values above are sRGB) ----
        public static Color Fur => FromSrgb(FurHex);
        public static Color FurDark => FromSrgb(FurDarkHex);
        public static Color Cream => FromSrgb(CreamHex);
        public static Color Wood => FromSrgb(WoodHex);
        public static Color WoodFrame => FromSrgb(WoodFrameHex);
        public static Color BarrierTeal => FromSrgb(BarrierTealHex);
        public static Color BarrierOrange => FromSrgb(BarrierOrangeHex);
        public static Color Terracotta => FromSrgb(TerracottaHex);
        public static Color Asphalt => FromSrgb(AsphaltHex);
        public static Color Curb => FromSrgb(CurbHex);

        /// <summary>
        /// Atlas regions of <c>Textures/Cat_1024.png</c>, in UV space (x = u, y = v,
        /// width = u span, height = v span). u wraps around the model, v is vertical.
        /// Kept here so tests can assert that every generated UV stays inside a region.
        /// </summary>
        public static class CatAtlas
        {
            public static readonly Rect Body = new Rect(0.00f, 0.00f, 0.50f, 0.50f);
            public static readonly Rect FurFlat = new Rect(0.00f, 0.50f, 0.25f, 0.25f);
            public static readonly Rect Cream = new Rect(0.25f, 0.50f, 0.25f, 0.25f);
            public static readonly Rect Leg = new Rect(0.00f, 0.75f, 0.25f, 0.25f);
            public static readonly Rect Tail = new Rect(0.25f, 0.75f, 0.25f, 0.25f);
            public static readonly Rect Head = new Rect(0.50f, 0.00f, 0.50f, 0.50f);
            public static readonly Rect Muzzle = new Rect(0.50f, 0.50f, 0.25f, 0.25f);

            /// <summary>Body ring mapping: u = 0 is the belly, u = 0.5 the spine, u = 1 the belly again.</summary>
            public const float BodyBellyU = 0.0f;
            public const float BodySpineU = 0.5f;

            /// <summary>Body ring mapping: v = 0 is the tail end, v = 0.5 the chest.</summary>
            public const float BodyTailV = 0.0f;
            public const float BodyChestV = 0.5f;
        }

        /// <summary>Convert an sRGB hex string to a linear Unity color without UnityEditor.</summary>
        public static Color FromSrgb(string hex)
        {
            if (string.IsNullOrEmpty(hex) || hex[0] != '#' || hex.Length != 7)
            {
                return Color.magenta; // loud, so a bad value cannot ship silently
            }
            int packed = 0;
            for (int i = 1; i < 7; i++)
            {
                int digit = System.Uri.IsHexDigit(hex[i]) ? System.Convert.ToInt32(hex[i].ToString(), 16) : -1;
                if (digit < 0)
                {
                    return Color.magenta;
                }
                packed = (packed << 4) | digit;
            }
            float r = ((packed >> 16) & 0xFF) / 255f;
            float g = ((packed >> 8) & 0xFF) / 255f;
            float b = (packed & 0xFF) / 255f;
            return new Color(ToLinear(r), ToLinear(g), ToLinear(b), 1f);
        }

        private static float ToLinear(float channel)
        {
            return channel <= 0.04045f
                ? channel / 12.92f
                : Mathf.Pow((channel + 0.055f) / 1.055f, 2.4f);
        }
    }
}
