// Source: YARA rule writing docs — structural illustration of tags + imports.
// https://yara.readthedocs.io/en/stable/writingrules.html
// Public documentation example. CCCS meta intentionally omitted — this
// fixture exercises the "non_cccs" tier path.

import "pe"

rule SuspiciousWebShell : webshell php
{
    meta:
        description = "Illustrative PHP webshell structural example."
        author      = "zettelforge-fixtures"
    strings:
        $eval      = "eval($_POST" ascii
        $assert    = "assert($_GET" ascii
        $base64    = "base64_decode(" ascii
    condition:
        any of them and filesize < 50KB
}
