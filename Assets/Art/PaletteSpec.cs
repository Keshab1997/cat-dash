using UnityEngine;

namespace CatDash.Art
{
    /// <summary>
    /// Single source of truth for the Cat Dash palette and the cat texture atlas regions.
    /// Values mirror the colours baked by the procedural generators
    /// (<c>tool/blender_cat.py</c>, <c>tool/blender_propset.py</c>, <c>tool/blender_road.py</c>);
    /// if a colour changes in a generator it must change here in the same commit.
    ///
    /// The cat and prop values were re-sampled from the owner-approved references
    /// (<c>docs/art/refs/cat-v2-stylized-3d-render.png</c>,
    /// <c>docs/art/refs/props-road-sheet.png</c>) when Agent B rebuilt the assets.
    ///
    /// Radius: Agent B (batch CD-B1). Lives in the <c>CatDash.Art</c> assembly next to the
    /// generated FBX files. Agent C's scene generator may reference <c>CatDash.Art</c> from
    /// <c>CatDash.Editor</c>; that one-line asmdef reference change is Captain-owned.
    /// </summary>
    public static class PaletteSpec
    {
        // ---- Cat (Assets/Art/Generated/Cat.fbx, atlas Textures/Cat_1024.png) ----
        public const string FurHex = "#D9944F";
        public const string FurLightHex = "#E8AC6B";
        public const string FurStripeHex = "#9A4A15";
        public const string FurStripeDarkHex = "#7A3A10";
        public const string CreamHex = "#FBF1DE";
        public const string CreamWarmHex = "#F3E0C0";
        public const string NoseHex = "#DE8A85";
        public const string EarPinkHex = "#DD9490";
        public const string EyeIrisHex = "#2FA48C";
        public const string EyeIrisDarkHex = "#1B7365";
        public const string EyePupilHex = "#12201F";
        public const string EyeScleraHex = "#F7F2E7";
        public const string EyeRimHex = "#3B2415";

        // ---- Props ---------------------------------------------------------------
        public const string WoodHex = "#D9A96C";
        public const string WoodDarkHex = "#A9763C";
        public const string WoodLightHex = "#E7BE86";
        public const string WoodFrameHex = "#E4CBA0";
        public const string CrateTealHex = "#3FA79B";
        public const string BarrierOrangeHex = "#EE9A4E";
        public const string BarrierCreamHex = "#F6E7C4";
        public const string TerracottaHex = "#C4623C";
        public const string LeafHex = "#5FA24A";
        public const string SoilHex = "#4A3524";

        // ---- Road / street -------------------------------------------------------
        public const string AsphaltHex = "#54555A";
        public const string LineWhiteHex = "#F2E7C9";
        public const string PavingHex = "#E3D6B4";
        public const string CurbHex = "#EFE5C8";

        // ---- Typed colours (Unity Color is linear; hex values above are sRGB) ----
        public static Color Fur => FromSrgb(FurHex);
        public static Color FurStripe => FromSrgb(FurStripeHex);
        public static Color Cream => FromSrgb(CreamHex);
        public static Color EyeIris => FromSrgb(EyeIrisHex);
        public static Color Nose => FromSrgb(NoseHex);
        public static Color Wood => FromSrgb(WoodHex);
        public static Color CrateTeal => FromSrgb(CrateTealHex);
        public static Color BarrierOrange => FromSrgb(BarrierOrangeHex);
        public static Color BarrierCream => FromSrgb(BarrierCreamHex);
        public static Color Terracotta => FromSrgb(TerracottaHex);
        public static Color Asphalt => FromSrgb(AsphaltHex);
        public static Color Curb => FromSrgb(CurbHex);

        /// <summary>
        /// Atlas regions of <c>Textures/Cat_1024.png</c>, in UV space (x = u, y = v,
        /// width = u span, height = v span). Every edge lands on a 64 px multiple so the
        /// generators' tiled grain stays seamless inside a region.
        /// Kept here so tests can assert that every generated UV stays inside a region.
        /// </summary>
        public static class CatAtlas
        {
            public static readonly Rect Body = new Rect(0.000f, 0.000f, 0.625f, 0.375f);
            public static readonly Rect Head = new Rect(0.625f, 0.000f, 0.375f, 0.375f);
            public static readonly Rect Leg = new Rect(0.000f, 0.375f, 0.250f, 0.250f);
            public static readonly Rect Tail = new Rect(0.250f, 0.375f, 0.375f, 0.250f);
            public static readonly Rect Ear = new Rect(0.625f, 0.375f, 0.250f, 0.250f);
            public static readonly Rect Eye = new Rect(0.875f, 0.500f, 0.125f, 0.125f);
            public static readonly Rect Muzzle = new Rect(0.000f, 0.625f, 0.375f, 0.375f);
            public static readonly Rect FurSpare = new Rect(0.625f, 0.625f, 0.375f, 0.375f);

            /// <summary>
            /// Body ring mapping inside <see cref="Body"/>: the ring wraps, so u = 0 (belly)
            /// and u = 1 are the same place on the model and the white belly wash is painted
            /// against both edges. u = 0.5 is the spine, where the "mouse" blaze sits.
            /// (Renamed from BodyBellyU/BodySpineU/BodyTailV/BodyChestV, which were absolute
            /// tile coordinates that stopped being true when the atlas was re-laid out; these
            /// are region-relative fractions, so they survive a future re-layout.)
            /// </summary>
            public const float BodyBellyAtU = 0.0f;
            public const float BodySpineAtU = 0.5f;

            /// <summary>Body ring mapping inside <see cref="Body"/>: v = 0 is the tail end, v = 1 the chest.</summary>
            public const float BodyTailAtV = 0.0f;
            public const float BodyChestAtV = 1.0f;
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
