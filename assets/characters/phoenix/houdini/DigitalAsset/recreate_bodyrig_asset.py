"""Recreate BodyRig as a clean HDA candidate from the current master rig scene."""

from __future__ import annotations

import os

try:
    hou  # type: ignore[name-defined]
except NameError:
    import hou  # type: ignore


HERE = os.path.dirname(os.path.abspath(__file__))
PHOENIX_ROOT = os.path.dirname(HERE)
SOURCE_HIP = os.path.join(PHOENIX_ROOT, "phoenix_character_rig.hipnc")
CANDIDATE_HDA = os.path.join(HERE, "BodyRig_recreated_candidate.hdanc")
TYPE_NAME = "tamadon::wings::1.0"


def main() -> None:
    hou.hipFile.load(SOURCE_HIP, suppress_save_prompt=True)
    obj = hou.node("/obj")
    feather_source = obj.node("feather_flow_guides")
    character_rig = obj.node("phoenix_character_rig")
    if feather_source is None or character_rig is None:
        raise RuntimeError("The source scene must contain feather_flow_guides and phoenix_character_rig")

    container = obj.createNode("subnet", "BodyRig_recreated")
    hou.moveNodesTo((feather_source, character_rig), container)
    feather_source = container.node("feather_flow_guides")
    character_rig = container.node("phoenix_character_rig")

    # The source object remains cookable for Object Merge, but only the final
    # character is visible until the promoted guide toggle is enabled.
    feather_source.parm("display").set(0)
    character_rig.parm("display").set(1)

    asset = container.createDigitalAsset(
        name=TYPE_NAME,
        hda_file_name=CANDIDATE_HDA,
        description="Wings",
        min_num_inputs=0,
        max_num_inputs=0,
        compress_contents=False,
        comment="Phoenix body rig, procedural feathers, and animation controls",
        version="1.0",
        create_backup=True,
    )

    # Validate that reparenting converted all critical references to paths that
    # remain inside the asset instead of depending on nodes at /obj.
    internal_rig = asset.node("phoenix_character_rig")
    critical = {
        "source wing": internal_rig.node("SOURCE_FEATHER_WING").parm("objpath1").rawValue(),
        "source transform": internal_rig.node("SOURCE_WING_TO_CHARACTER_SPACE").parm("tx").rawValue(),
        "growth": asset.node("feather_flow_guides/oil_growth").parm("progress").rawValue(),
    }
    for label, value in critical.items():
        if value.startswith("/obj/") or '"/obj/' in value:
            raise RuntimeError(f"External path remained for {label}: {value}")

    output = internal_rig.node("OUT_PHOENIX_CHARACTER")
    output.geometry()
    if output.errors():
        raise RuntimeError("Recreated rig cook errors: " + "\n".join(output.errors()))

    print("Candidate:", CANDIDATE_HDA)
    print("Definition:", asset.type().name())
    print("Internal paths:", critical)


if __name__ == "__main__":
    main()
