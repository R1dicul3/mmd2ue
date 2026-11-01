# mmd2ue - MMD (PMX/VMD/VPD) to UE5.8 conversion toolkit (stage 1: M0 + M1)
# Core layer only. Parsers do NOT import unreal (constraints C2/C3).

from mmd2ue.core.ir import IR_VERSION

__version__ = "0.2.0"
__all__ = ["IR_VERSION", "__version__"]
