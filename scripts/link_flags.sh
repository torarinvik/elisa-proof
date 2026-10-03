# shellcheck shell=bash
# Sourced by build.sh, test.sh and dogfood.sh: the flags that dead-strip a linked Elisa product.
# Apple ld spells it -dead_strip. GNU ld spells it --gc-sections, needs -no-pie because the
# compiler's objects are not position independent, and needs libm, which Apple's libSystem
# carries implicitly; --no-as-needed keeps libm even though it precedes the objects.
if [[ "$(uname -s)" == "Darwin" ]]; then
    ELISA_DEAD_STRIP_LINK=(-Wl,-dead_strip)
else
    ELISA_DEAD_STRIP_LINK=(-no-pie -Wl,--gc-sections -Wl,--no-as-needed -lm)
fi
