from PIL import Image
from pathlib import Path

base = Path("phoenix_parts")
base.mkdir(exist_ok=True)

files = ['body.png', 'head.png', 'beak_upper.png', 'beak_lower.png', 'neck_01.png', 'neck_02.png', 'neck_03.png', 'wing_L_upper.png', 'wing_L_mid.png', 'wing_L_tip.png', 'wing_R_upper.png', 'wing_R_mid.png', 'wing_R_tip.png', 'wing_L_feather_01.png', 'wing_L_feather_02.png', 'wing_L_feather_03.png', 'wing_R_feather_01.png', 'wing_R_feather_02.png', 'wing_R_feather_03.png', 'tail_base.png', 'tail_01.png', 'tail_02.png', 'tail_03.png', 'tail_04.png', 'tail_05.png', 'tail_06.png', 'crest_01.png', 'crest_02.png', 'crest_03.png', 'leg_L.png', 'foot_L.png', 'leg_R.png', 'foot_R.png', 'flame_01.png', 'flame_02.png', 'flame_03.png', 'flame_04.png', 'flame_05.png']

blank = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
for filename in files:
    blank.save(base / filename, "PNG")

print("Generated", len(files), "transparent PNG placeholders.")
for filename in files:
    print(filename)
