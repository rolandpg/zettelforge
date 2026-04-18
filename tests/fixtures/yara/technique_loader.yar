// Source: CCCS-Yara README sample "MemoryModule" technique rule.
// https://github.com/CybercentreCanada/CCCS-Yara/blob/master/README.md
// MIT license per upstream. The meta block follows CCCS_YARA.yml schema
// (category=TECHNIQUE + technique + author@ORG + mitre_att + sharing).

rule MemoryModule {
    meta:
        author      = "analyst@CCCS"
        description = "Detects the MemoryModule PE-loader technique used to load DLLs directly from memory."
        category    = "TECHNIQUE"
        technique   = "loader:memorymodule"
        mitre_att   = "T1218"
        sharing     = "TLP:WHITE"
        source      = "CCCS"
        status      = "RELEASED"
        version     = "1.0"
    strings:
        $func1 = "MemoryLoadLibrary"
        $func2 = "MemoryGetProcAddress"
        $func3 = "MemoryFreeLibrary"
    condition:
        2 of ($func*)
}
