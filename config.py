"""
Registry of every source the scraper pulls from.

Each ATS entry was verified to return a live public job feed (Sep 2026).
Add a firm by appending a tuple: (display name, slug).  Slugs are the
board id you see in the firm's careers URL, e.g.
  boards.greenhouse.io/<slug>, jobs.lever.co/<slug>, jobs.ashbyhq.com/<slug>
"""

# ---------------------------------------------------------------- ATS feeds
GREENHOUSE = [
    ("Jane Street", "janestreet"),
    ("Hudson River Trading", "wehrtyou"),
    ("Optiver", "optiverus"),
    ("DRW", "drweng"),
    ("IMC Trading", "imc"),
    ("Akuna Capital", "akunacapital"),
    ("Jump Trading", "jumptrading"),
    ("Old Mission", "oldmissioncapital"),
    ("Tower Research Capital", "towerresearchcapital"),
    ("Five Rings", "fiveringsllc"),
    ("Flow Traders", "flowtraders"),
    ("Chicago Trading Company", "chicagotrading"),
    ("Point72", "point72"),
    ("Qube Research & Technologies", "quberesearchandtechnologies"),
    ("Squarepoint Capital", "squarepointcapital"),
    ("TransMarket Group", "transmarketgroup"),
    ("DV Trading", "dvtrading"),
    ("Geneva Trading", "genevatrading"),
    ("AQR Capital", "aqr"),
    ("WorldQuant", "worldquant"),
    ("Schonfeld", "schonfeld"),
    ("ExodusPoint", "exoduspoint"),
    ("PDT Partners", "pdtpartners"),
    ("Capstone Investment Advisors", "capstoneinvestmentadvisors"),
    ("Mako Trading", "mako"),
    ("Engineers Gate", "engineersgate"),
    ("Vatic Labs", "vaticlabs"),
    ("Virtu Financial", "virtu"),
    ("Man Group", "mangroup"),
    ("Quadrature", "quadraturecapital"),
    ("3Red Partners", "3redpartners"),
    ("Eclipse Trading", "eclipsetrading"),
    ("Gelber Group", "gelbergroup"),
    ("Trillium", "trillium"),
    ("Simplex Trading", "simplextrading"),
    ("Epoch Capital", "epochcapital"),
    ("Capital Fund Management", "cfm"),
    ("Galaxy", "galaxy"),
    ("Winton", "winton"),
    ("AlphaGrep", "alphagrepsecurities"),
    ("Tanius Technology", "tanius"),
    ("Aquatic Capital", "aquaticcapitalmanagement"),
    ("VivCourt", "vivcourt"),
]

LEVER = [
    ("Belvedere Trading", "belvederetrading"),
    ("Valkyrie Trading", "valkyrietrading"),
    ("Ansatz Capital", "ansatzcapital"),
]

ASHBY = [
    ("Voleon", "voleon"),
    ("Jump Trading", "jump"),
]

# ------------------------------------------------ plain-HTML careers pages
# Best effort: we pull every link whose text looks like an internship.
# Pages that render jobs with JavaScript will simply yield nothing.
HTML_PAGES = [
    ("D. E. Shaw", "https://www.deshaw.com/careers/internships"),
    ("Two Sigma", "https://careers.twosigma.com/careers/OpenRoles?Roles=Intern"),
    ("Citadel", "https://www.citadel.com/careers/open-opportunities/students/"),
    ("Citadel Securities", "https://www.citadelsecurities.com/careers/open-opportunities/students/"),
    ("Susquehanna (SIG)", "https://careers.sig.com/recent-graduate/jobs"),
    ("XTX Markets", "https://www.xtxmarkets.com/careers/"),
    ("G-Research", "https://www.gresearch.com/vacancies/"),
    ("Radix Trading", "https://radix-trading.com/careers"),
    ("Headlands Technologies", "https://www.headlandstech.com/careers"),
    ("Wolverine Trading", "https://www.wolve.com/careers"),
    ("Millennium", "https://www.mlp.com/campus-programs/"),
    ("Balyasny Asset Management", "https://www.bamfunds.com/campus"),
    ("Bridgewater Associates", "https://www.bridgewater.com/working-at-bridgewater/students"),
    ("Cubist (Point72)", "https://www.point72.com/cubist/"),
    ("Marshall Wace", "https://www.mwam.com/careers/"),
    ("Susquehanna (SIG) - Bala", "https://careers.sig.com/jobs"),
]

# ---------------------------------------------------- GitHub-maintained lists
GITHUB_LISTS = [
    # (name, raw README url, parser key, level hint: "Internship" | "New Grad" | None)
    ("SimplifyJobs Summer 2027", "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md", "simplify", "Internship"),
    ("Northwestern Quant Internships 2027", "https://raw.githubusercontent.com/northwesternfintech/2027QuantInternships/main/README.md", "nwquant", "Internship"),
    ("vanshb03 Summer 2027", "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/main/README.md", "vansh", "Internship"),
    ("SimplifyJobs New Grad", "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md", "simplify", "New Grad"),
    ("vanshb03 New Grad 2027", "https://raw.githubusercontent.com/vanshb03/New-Grad-2027/main/README.md", "vansh", "New Grad"),
]

# A posting is a new-grad / entry-level role if it hits one of these (and isn't an internship)
NEWGRAD_PATTERNS = [
    r"\bnew[- ]grad(uate)?s?\b", r"\bgraduate (program|programme|scheme|hire|role|analyst|engineer|trader|researcher|developer|software|trainee)\b",
    r"\bentry[- ]level\b", r"\bearly[- ]career\b", r"\bcampus (hire|program|programme|recruit)", r"\buniversity (grad|hire|program)",
    r"\b(class of|graduating in) 20\d\d\b", r"\b20\d\d (grad|start|graduates?)\b", r"\banalyst program(me)?\b",
    r"\bjunior (trader|quant|developer|engineer|researcher|analyst)\b", r"\btrainee\b", r"\bassociate program(me)?\b",
    r"\bph\.?d (grad|hire)", r"\bgrad(uate)? (quant|trader|developer|software|hire)", r"\b(full[- ]time|ft) (grad|new)",
]

# ---------------------------------------------------------- LinkedIn search
LINKEDIN_QUERIES = [
    ("quantitative trading intern", "United States"),
    ("quantitative research intern", "United States"),
    ("quantitative developer intern", "United States"),
    ("quantitative analyst intern", "United States"),
    ("trading intern 2027", "United States"),
    ("quant intern", "London, England, United Kingdom"),
    ("quant intern", "Chicago, Illinois, United States"),
    ("quant intern", "New York, United States"),
]

# ------------------------------------------------------------ classification
# A posting is an internship if the title (or ATS department) hits one of these
INTERN_PATTERNS = [
    r"\bintern(ship|ships)?\b", r"\bsummer analyst\b", r"\bco-?op\b",
    r"\bindustrial placement\b", r"\bindustry placement\b", r"\bplacement year\b",
    r"\bwinternship\b", r"\b(summer|spring|fall|autumn|winter)\s*20\d\d\b",
    r"\bcampus\b", r"\bstudent\b", r"\bsummer program(me)?\b", r"\bfellowship\b",
]

# For generic sources (LinkedIn, Simplify, ...) a posting must look quant-ish
QUANT_PATTERNS = [
    r"\bquant", r"\btrading\b", r"\btrader\b", r"\balgorithmic\b", r"\bmarket[- ]mak",
    r"\bhft\b", r"\bsystematic\b", r"\bderivatives?\b", r"\boptions\b",
    r"\bproprietary\b", r"\bhedge fund\b", r"\bfixed income\b", r"\bstrats?\b",
    r"\blow[- ]latency\b", r"\bequities\b", r"\bcapital markets\b",
]

# Different spellings of the same firm across sources -> one display name
COMPANY_ALIASES = {
    "susquehanna": "Susquehanna (SIG)", "susquehanna international group": "Susquehanna (SIG)",
    "susquehanna investment group": "Susquehanna (SIG)", "sig": "Susquehanna (SIG)",
    "de shaw": "D. E. Shaw", "d.e. shaw": "D. E. Shaw", "d. e. shaw": "D. E. Shaw", "the d. e. shaw group": "D. E. Shaw",
    "jump trading group": "Jump Trading", "jump": "Jump Trading",
    "tower research": "Tower Research Capital", "virtu": "Virtu Financial",
    "the voleon group": "Voleon", "voleon group": "Voleon",
    "jp morgan chase": "JPMorgan", "jpmorgan chase": "JPMorgan", "jpmorgan chase & co.": "JPMorgan",
    "j.p. morgan": "JPMorgan", "jpmorganchase": "JPMorgan",
    "imc": "IMC Trading", "imc financial markets": "IMC Trading",
    "qube": "Qube Research & Technologies", "qube rt": "Qube Research & Technologies",
    "two sigma investments": "Two Sigma", "hudson river trading (hrt)": "Hudson River Trading", "hrt": "Hudson River Trading",
    "citadel llc": "Citadel", "citadel securities llc": "Citadel Securities",
    "dv group": "DV Trading", "chicago trading company (ctc)": "Chicago Trading Company", "ctc": "Chicago Trading Company",
    "akuna": "Akuna Capital", "five rings capital": "Five Rings", "old mission capital": "Old Mission",
    "point72 asset management": "Point72", "squarepoint": "Squarepoint Capital",
    "aqr": "AQR Capital", "aqr capital management": "AQR Capital",
    "millennium management": "Millennium", "millennium partners": "Millennium",
    "balyasny": "Balyasny Asset Management", "bam": "Balyasny Asset Management",
    "bridgewater": "Bridgewater Associates", "optiver us": "Optiver",
    "aquatic": "Aquatic Capital", "aquatic capital management": "Aquatic Capital",
    "alphagrep securities": "AlphaGrep", "cfm": "Capital Fund Management",
    "capstone": "Capstone Investment Advisors", "mako": "Mako Trading",
    "flow traders us": "Flow Traders", "man group plc": "Man Group",
    "goldman sachs & co": "Goldman Sachs", "morgan stanley & co": "Morgan Stanley",
    "intercontinental exchange, inc.": "Intercontinental Exchange", "intercontinental exchange, i": "Intercontinental Exchange",
    "voloridge investment management": "Voloridge", "quantbot": "Quantbot Technologies",
}

# Titles matching these are never quant internships even if they say "intern"
EXCLUDE_PATTERNS = [
    r"\brecruit(er|ing)\b", r"\bhuman resources\b", r"\bmarketing\b", r"\bsales\b",
    r"\bfacilities\b", r"\breceptionist\b", r"\bchef\b", r"\bexecutive assistant\b",
    r"\blegal\b", r"\bcompliance\b", r"\baccounting\b", r"\btax\b", r"\bpayroll\b",
    r"\bcommunications\b", r"\bevents?\b", r"\boffice\b", r"\bdesign(er)?\b",
]

# Category rules are evaluated in order; first match wins
CATEGORY_RULES = [
    ("Quant Trading",  [r"\btrad(er|ing)\b", r"\bmarket[- ]mak", r"\bqt\b"]),
    ("Quant Research", [r"\bquant(itative)? research", r"\bresearch(er)?\b", r"\bqr\b", r"\bquantitative analyst\b", r"\bquant(itative)? strateg", r"\bstrats?\b", r"\bscientist\b"]),
    ("Quant Dev",      [r"\bquant(itative)? dev", r"\bqd\b", r"\bquantitative engineer", r"\bquant(itative)? technolog"]),
    ("Data & ML",      [r"\bmachine learning\b", r"\bml\b", r"\bai\b", r"\bdata scien", r"\bdata analyst\b", r"\bdata engineer", r"\bnlp\b"]),
    ("Hardware/FPGA",  [r"\bfpga\b", r"\bhardware\b", r"\basic\b", r"\belectrical\b", r"\bverilog\b"]),
    ("Software Eng",   [r"\bsoftware\b", r"\bswe\b", r"\bengineer(ing)?\b", r"\bdeveloper\b", r"\bprogrammer\b", r"\bdevops\b", r"\bsre\b", r"\binfrastructure\b", r"\bsystems?\b", r"\bsecurity\b", r"\bnetwork", r"\bplatform\b", r"\bc\+\+\b", r"\bpython\b", r"\bfull[- ]stack\b", r"\bweb\b", r"\bcloud\b", r"\btechnolog", r"\bfrontend\b", r"\bux\b", r"\bit\b"]),
    ("Quant Research", [r"\bquant"]),          # "Quantitative Intern", "Quant Intern - Analytics"
    ("Finance/Ops",    [r"\bfinance\b", r"\bfinancial\b", r"\brisk\b", r"\boperations\b", r"\binvestment\b", r"\banalyst\b", r"\bbusiness\b", r"\bproduct\b", r"\bcredit\b", r"\bfixed income\b"]),
]

# Location hubs: label -> patterns matched against the raw location string
HUBS = [
    ("New York",   [r"\bnew york\b", r"\bnyc\b", r"\bmanhattan\b", r"\bjersey city\b", r"\bbrooklyn\b", r"\bny\b"]),
    ("Chicago",    [r"\bchicago\b", r"\bil\b"]),
    ("Bay Area",   [r"\bsan francisco\b", r"\bsf\b", r"\bbay area\b", r"\bpalo alto\b", r"\bmenlo park\b", r"\bmountain view\b", r"\bberkeley\b", r"\bsunnyvale\b", r"\bsan jose\b", r"\bredwood city\b", r"\bsan mateo\b"]),
    ("Boston",     [r"\bboston\b", r"\bcambridge, ma\b", r"\bma\b"]),
    ("Connecticut",[r"\bgreenwich\b", r"\bstamford\b", r"\bconnecticut\b", r"\bct\b"]),
    ("Philadelphia",[r"\bphiladelphia\b", r"\bbala cynwyd\b", r"\bpa\b"]),
    ("Austin",     [r"\baustin\b"]),
    ("Miami",      [r"\bmiami\b", r"\bfl\b"]),
    ("Houston",    [r"\bhouston\b", r"\btx\b"]),
    ("Los Angeles",[r"\blos angeles\b", r"\bla\b", r"\bsanta monica\b", r"\bpasadena\b"]),
    ("Seattle",    [r"\bseattle\b", r"\bbellevue\b", r"\bwa\b"]),
    ("Other US",   [r"\bunited states\b", r"\busa\b", r"\bus\b", r"\bwashington\b", r"\bdenver\b", r"\bpittsburgh\b", r"\batlanta\b"]),
    ("London",     [r"\blondon\b", r"\buk\b", r"\bunited kingdom\b", r"\bengland\b"]),
    ("Amsterdam",  [r"\bamsterdam\b", r"\bnetherlands\b"]),
    ("Europe",     [r"\bparis\b", r"\bdublin\b", r"\bzurich\b", r"\bzug\b", r"\bfrankfurt\b", r"\bmadrid\b", r"\bmilan\b", r"\bstockholm\b", r"\bgeneva\b", r"\bcopenhagen\b", r"\bfrance\b", r"\bgermany\b", r"\bireland\b", r"\bswitzerland\b"]),
    ("Hong Kong",  [r"\bhong kong\b", r"\bhk\b"]),
    ("Singapore",  [r"\bsingapore\b"]),
    ("Asia",       [r"\bshanghai\b", r"\bbeijing\b", r"\btokyo\b", r"\bmumbai\b", r"\bbangalore\b", r"\bbengaluru\b", r"\bgurgaon\b", r"\bgurugram\b", r"\bhyderabad\b", r"\bindia\b", r"\bchina\b", r"\bjapan\b", r"\btaipei\b", r"\bseoul\b", r"\bdubai\b"]),
    ("Australia",  [r"\bsydney\b", r"\bmelbourne\b", r"\bbrisbane\b", r"\baustralia\b"]),
    ("Remote",     [r"\bremote\b"]),
]

# Names of quant firms (lower-cased substrings) used to accept postings from
# generic sources even when the title doesn't say "quant".
QUANT_FIRM_NAMES = [n.lower() for n, _ in GREENHOUSE + LEVER + ASHBY + HTML_PAGES] + [
    "citadel", "two sigma", "jane street", "hudson river", "hrt", "susquehanna", "sig",
    "de shaw", "d. e. shaw", "d.e. shaw", "millennium", "bridgewater", "renaissance",
    "xtx", "g-research", "radix", "headlands", "wolverine", "balyasny", "cubist",
    "marshall wace", "peak6", "tibra", "group one", "da vinci", "maven", "quantlab",
    "arrowstreet", "walleye", "trexquant", "tudor", "verition", "graham capital",
    "jain global", "seven eight", "teza", "alphadyne", "kershner", "bluefin", "volant",
    "marquette", "tgs", "sunrise futures", "prime trading", "hehmeyer", "gsr",
    "wintermute", "cumberland", "systematica", "aspect capital", "elliott", "bluecrest",
    "brevan howard", "numerai", "symmetry investments", "hap capital", "bracebridge",
    "sculptor", "blackrock", "goldman sachs", "morgan stanley", "jpmorgan", "j.p. morgan",
    "bank of america", "barclays", "ubs", "deutsche bank", "nomura", "jefferies",
    "wells fargo", "cboe", "cme group", "nasdaq", "nyse", "ice ", "intercontinental exchange",
    "fidelity", "vanguard", "state street", "pimco", "wellington", "t. rowe", "franklin",
    "invesco", "moody", "s&p global", "msci", "bloomberg", "factset", "optiver", "imc",
    "flow traders", "akuna", "drw", "jump", "tower research", "five rings", "old mission",
    "belvedere", "chicago trading", "ctc", "transmarket", "dv trading", "geneva trading",
    "aqr", "worldquant", "schonfeld", "exoduspoint", "pdt", "capstone", "mako",
    "engineers gate", "vatic", "virtu", "man group", "quadrature", "3red", "eclipse trading",
    "gelber", "trillium", "simplex", "epoch", "cfm", "winton", "alphagrep", "tanius",
    "aquatic", "vivcourt", "voleon", "valkyrie", "ansatz", "squarepoint", "qube", "point72",
]
