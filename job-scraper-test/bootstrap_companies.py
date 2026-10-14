"""One-off: build companies.json by probing Greenhouse / Lever / Ashby for candidate companies.

Candidates = boards seen in web search results + a hand-made list of India-hiring
startups, product companies and global companies with Indian engineering offices.
Each candidate's likely slugs are tried on all three public APIs (one call per try);
a board is kept only if it exists AND currently lists at least one India /
remote-India job. Re-running merges with an existing companies.json (keeps `active`).

Usage: python bootstrap_companies.py [--out companies.json]
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

import ats

STACK_RE = re.compile(r"flutter|python|django|fast\s?api|react|full[\s-]?stack|backend|back-end|mobile|software engineer|sde", re.I)

# Boards that appeared in web search results (Oct 2026): (name, ats, slug, query)
FROM_SEARCH = [
    ("Safe Security", "lever", "safe", 'site:jobs.lever.co Bengaluru software engineer'),
    ("Acceldata", "lever", "acceldata", 'site:jobs.lever.co Bengaluru software engineer'),
    ("LinkedIn", "lever", "linkedin", 'site:jobs.lever.co Bengaluru software engineer'),
    ("Atomicwork", "greenhouse", "atomicwork", 'site:job-boards.greenhouse.io Bengaluru India software engineer'),
    ("Meltplan", "greenhouse", "meltplan", 'site:job-boards.greenhouse.io Bengaluru India software engineer'),
    ("GetWellNetwork", "greenhouse", "getwellnetwork", 'site:job-boards.greenhouse.io Bengaluru India software engineer'),
    ("Smart Working Solutions", "lever", "smart-working-solutions", 'site:jobs.ashbyhq.com "Remote - India" OR Bangalore'),
    ("Gruve", "greenhouse", "gruve", 'site:boards.greenhouse.io Bangalore OR Gurugram OR Pune engineer India'),
    ("ConverseNow", "lever", "ConverseNow", 'lever.co Bangalore India backend engineer Python job posting'),
    ("Gushwork", "lever", "gushwork", 'lever.co Bangalore India backend engineer Python job posting'),
    ("Jobgether", "lever", "jobgether", 'jobs.lever.co Mobile Application Developer Gurugram'),
    ("Energy Tech Global", "greenhouse", "energytechglobal", 'boards.greenhouse.io Software Developer Hyderabad'),
    ("Atlassian", "lever", "atlassian", 'jobs.lever.co SDE 1 Bangalore'),
]

# India-based / India-hiring company names found via web search & pages (Oct 2026). Boards found for
# these are kept even with no India-tagged opening today (the company is India-based).
INDIA_NAME_SOURCES = {
    "web search: jobs.ashbyhq.com / boards.greenhouse.io role x city queries": [
        "Cartesia", "FurtherAI", "Skeps", "Capillary Technologies", "WorkIndia", "Kratikal", "BeyondScale",
        "Code Vyasa", "Hiver", "CARD91", "GoDaddy", "Tower Research", "Forty4 Technologies", "Three Across",
        "OfBusiness", "Josh Technology Group", "Urban Company", "Slice", "Eternal", "District", "Paisabazaar",
        "CoTrav", "Lepton Software", "Cloud Counselage", "Spenmo", "LiteLLM", "Human Archive"],
    "vcbacked.co YC companies in Bengaluru/Gurugram": [
        "Ressl AI", "Ritivel", "Truffle AI", "Infinity", "xPay", "Yenmo", "Clueso", "CodeParrot AI", "DrDroid",
        "Floworks", "Mantys", "SuperKalam", "AntWalk", "BharatX", "Blitzllama", "Castled.io", "Fello",
        "Material Depot", "MySivi", "PayCrunch", "RecordBook", "Rehook.ai", "SALT", "Bimaplan", "BusinessOnBot",
        "Codingal", "Dyte", "Flux Auto", "FanPlay", "RocketSDR", "Voosh", "Weekday", "Rowboat Labs", "CheqUPI",
        "100x", "CompUp", "Coupl", "FlatX", "Gullak Money", "Integration Labs", "Maya Labs", "Peoplebox.ai",
        "Raven", "Shelf", "SigmaMind AI", "Antropi Robotics", "Bolna AI", "YourQuote", "Zealth", "ZOKO",
        "Chaos Genius", "DocVita", "farmtheory", "Morphle Labs", "Spenny", "StayQrious", "Synapsica", "Inito",
        "Mudrex", "Akudo", "Coulomb AI", "FrontPage", "Ivy Homes", "Karbon Card", "Koshex", "marketfeed",
        "Rivia.AI", "SalaryBook", "Spark Studio", "Stownest", "Cradle", "Decentro", "Explorex", "Jeevam Health",
        "MedPiper", "Orange Health", "Volopay", "WareIQ", "Binks", "FamPay", "Lokal", "Namaste Business",
        "Vahan", "Wingman", "Khatabook", "OkCredit", "Better Opinions", "Kaagaz", "RDash", "Bueno Finance",
        "GroMo", "Invoid", "Pensil", "zingbus", "Kosh", "AccioJob", "Kisan Network", "Waybill", "Paasa",
        "Clinikally", "Advantage Club", "Novatr", "SalaryBox", "Farmako", "Statiq"],
    "fueler.io: Bengaluru startups hiring in 2026": [
        "GrowthX", "SpotDraft", "Nanonets", "Pixis", "Murf AI", "Xoxoday", "Botsync", "Fulfil", "ENGinPilot",
        "Troopod", "genieX", "Atherna", "SignSetu", "Fireflies.ai", "Slikk", "Clientell AI", "ChiefPulse",
        "6sense", "SingleStore", "Cekura", "Cyble", "Samora AI", "SaralX", "Emergent", "AiPrise", "Cardboard",
        "Tsenta", "Deepvue.ai", "iMerlin", "Leucine", "FOXO", "ownpath", "Havi", "BrandBrahma", "Cube",
        "Asymmetric Labs", "Richpanel", "Outdoo AI", "Variabl", "Yug Brands", "VideoDB", "ToolJet", "Bureau",
        "Atlys", "Maxim AI"],
    "YC India jobs board (ycombinator.com/jobs/role/software-engineer/india)": ["Spenmo", "LiteLLM", "Human Archive"],
}

# Candidate companies (India-hiring). Slugs are guessed from the name; extra spellings in ALIASES.
CANDIDATES = """
Razorpay; CRED; Groww; Zerodha; Meesho; Swiggy; Zomato; PhonePe; Paytm; Flipkart; Myntra; Ola; Dunzo;
Urban Company; Nykaa; Lenskart; boAt; Mamaearth; ShareChat; Dailyhunt; InMobi; Glance; Postman; BrowserStack;
Freshworks; Chargebee; Druva; Hasura; Appsmith; ToolJet; Setu; Juspay; Slice; Jupiter; Fi Money; Niyo; smallcase;
Upstox; CoinDCX; CoinSwitch; Polygon; Zeta; Perfios; M2P Fintech; Cashfree; Khatabook; OkCredit; BharatPe;
Pine Labs; Instamojo; Yellow.ai; Haptik; Gupshup; Exotel; LeadSquared; Darwinbox; Keka; Springworks; Zluri;
Whatfix; MindTickle; Capillary; MoEngage; CleverTap; WebEngage; Netcore; Innovaccer; Practo; PharmEasy; Cult.fit;
HealthifyMe; Unacademy; Vedantu; upGrad; Scaler; Physics Wallah; Eruditus; Classplus; Testbook; Cuemath;
Leap Finance; KreditBee; Moneyview; Navi; Acko; Digit Insurance; Policybazaar; Plum; Onsurity; Rupeek; Licious;
Zepto; Blinkit; BigBasket; DealShare; Udaan; Jumbotail; Zetwerk; OfBusiness; Moglix; Delhivery; Shiprocket;
BlackBuck; Porter; Park+; Spinny; Cars24; CarDekho; Rapido; Yulu; Ather Energy; Ultrahuman; Headout; Apna;
Internshala; Unstop; Peerlist; Atlan; Hevo Data; Sarvam AI; Observe.AI; Uniphore; Rocketlane; SpotDraft;
Sprinto; Scrut Automation; Signeasy; Leena AI; Wingify; Interakt; Bitespeed; Plivo; MyGate; NoBroker;
Livspace; HomeLane; CityMall; Dukaan; Shopflo; GoKwik; Simpl; PayU; Easebuzz; Decentro; Signzy; IDfy;
HyperVerge; Bureau; Fampay; INDmoney; Kuvera; Fyers; Dhan; Sensibull; Dream11; Dream Sports; Games24x7; MPL;
WinZO; Zupee; Loco; Kuku FM; Pocket FM; STAGE; Seekho; Bewakoof; Snitch; Purplle; FirstCry; BlueStone;
Pepperfry; Wakefit; Furlenco; Zoomcar; Eightfold; HighRadius; Icertis; Ninjacart; Jar; Fold; Uolo; Trell;
Atlassian; Stripe; Coinbase; Databricks; Confluent; MongoDB; Elastic; Okta; Twilio; Cloudflare; Datadog;
Snowflake; Rubrik; Nutanix; Zscaler; GitLab; HashiCorp; Airbnb; DoorDash; Rippling; Deel; Remote; Intuit;
Grammarly; Harness; Gong; HubSpot; Zendesk; Dropbox; Pinterest; Reddit; Discord; Figma; Notion; Airtable;
Miro; Vercel; Supabase; PostHog; Sentry; Temporal; ClickHouse; Cockroach Labs; Yugabyte; Couchbase; Redis;
Mattermost; Zapier; Automattic; Toptal; Turing; Andela; Oyster; Instawork; Sprinklr; Chargebee; Clari;
Mindtickle; Hevo; Zuora; Freshdesk; Glean; Rubrik; Druva; Cohesity; Commvault; ThoughtSpot; Tekion;
Uber; Lyft; Wise; Revolut; Brex; Ramp; Plaid; Chime; Robinhood; Affirm; Adyen; Checkout.com; Klarna;
Tide; Monzo; N26; Mercury; Gusto; Lattice; Culture Amp; Personio; Hibob; Workato; Celonis; UiPath;
Postman; Agoda; Booking; Expedia; Trivago; Grab; Gojek; Sea; Shopee; Carousell; Xendit; Thoughtworks;
Sumo Logic; New Relic; Dynatrace; PagerDuty; LaunchDarkly; Amplitude; Mixpanel; Segment; Braze;
Optimizely; Contentful; Sanity; Strapi; Algolia; Twitch; Spotify; SoundCloud; Canva; Atlassian; Miro;
Freshworks; Zoho; Chargebee; Hotstar; JioCinema; Swiggy; Myntra; Tata 1mg; Tata Neu; Cleartrip; MakeMyTrip;
Ixigo; EaseMyTrip; Yatra; OYO; Treebo; FabHotels; Zostel; Unacademy; Toppr; BYJU'S; Great Learning;
Simplilearn; Coursera; Udemy; Duolingo; Quizlet; Brainly; Chegg; Course Hero; Nearpod; Kahoot;
Vahan; Pratilipi; Koo; Chingari; Josh; VerSe Innovation; Rooter; Eloelo; FRND; Kutumb; Glip;
Fractal; Tredence; Sigmoid; Quantiphi; LatentView; Mu Sigma; Tiger Analytics; Gramener; Course5;
Hasura; Appsmith; ToolJet; Plane; SigNoz; Middleware; Chatwoot; Dyte; 100ms; Fynd; Shiprocket;
Zocdoc; Nference; Qure.ai; SigTuple; Niramai; Tricog; Cloudphysician; Pristyn Care; Even Healthcare;
Medikabazaar; Truemeds; Tata Health; Mfine; DocsApp; Lybrate; Eka Care; Sukino; Ekincare
"""
CANDIDATES += """;
Wayfair; Fivetran; Samsara; Toast; Gainsight; Highspot; ServiceTitan; Procore; Arcesium; Addepar; Coupa; Qualys;
Avalara; Cvent; Kissflow; Hippo Video; Vue.ai; Facilio; SuperOps; Ideas2IT; Saama; Kore.ai; Phenom; Zenoti; Apty;
Josh Technology; Times Internet; Square Yards; OneCard; PubMatic; Mindbody; Tracxn; Zeotap; Media.net; Amagi;
Unbxd; Netomi; Kaleyra; Ozonetel; LambdaTest; Testsigma; Toddle; Teachmint; Masai School; Newton School; AlmaBetter;
Coding Ninjas; GeeksforGeeks; Airmeet; Hubilo; Bounce; Euler Motors; Log9; Exponent Energy; River; Ultraviolette;
Simple Energy; Agnikul; Skyroot; Pixxel; Digantara; ideaForge; FreshToHome; Country Delight; Vegrow; DeHaat;
AgroStar; Arya.ag; Cropin; Bizongo; Shadowfax; Xpressbees; Loadshare; ElasticRun; Arzooo; Vyapar; Open Financial;
Zaggle; Canonical; Hotjar; DuckDuckGo; Chainlink Labs; Consensys; Alchemy; Polygon Labs; Kraken; OKX; Bybit;
Crypto.com; Ripple; Fireblocks; Chainalysis; Gemini; Circle; Uniswap; Aave; Near; Solana; Aptos; Mysten Labs;
Biconomy; Push Protocol; Mudrex; ZebPay; Liminal; Instadapp; Router Protocol; QuickNode; Ankr; Covalent; The Graph;
Gorgias; Intercom; Front; Freshservice; Zylo; Lucidchart; Smartsheet; Asana; Monday; ClickUp; Coda; Linear;
Retool; Airbyte; dbt Labs; Fivetran; Hightouch; Census; Prefect; Dagster; Astronomer; Starburst; Dremio; Rockset;
Pinecone; Weaviate; Qdrant; Zilliz; LangChain; LlamaIndex; Hugging Face; Cohere; Anyscale; Modal; Replicate;
Together AI; Fireworks AI; Perplexity; Character AI; ElevenLabs; Synthesia; Runway; Jasper; Writer; Typeface;
Glean; Moveworks; Sierra; Decagon; Cresta; Observe.AI; Gupshup; Verloop; Kapture CX; Ameyo; Freshchat;
CleverTap; MoEngage; Netcore Cloud; Juspay; Setu; Perfios; Signzy; Karza; Digio; Leegality; SpotDraft;
Razorpay; Cashfree Payments; PayU India; Paytm Money; Groww; Smallcase; Scripbox; ET Money; Jar; Fold;
Kiwi; Uni Cards; OneCard; Slice; Jupiter; Fi; Freo; Niyo; Kotak811; Navi; Moneyview; KreditBee; Fibe;
Stashfin; Rupeek; Indifi; Lendingkart; FlexiLoans; Aye Finance; Progcap; Vayana; Credgenics; Recko; Ezetap;
Zolve; Atlys; Skyscanner; Klook; Pickyourtrail; Thrillophilia; Headout; Holidify; Scapia; Zostel;
Cure.fit; Tata Digital; Reliance Jio; Jio Platforms; Airtel X Labs; Wynk; Gaana; JioSaavn; Hungama; Zee5;
SonyLIV; ALTBalaji; Eros Now; MX Player; Moj; Josh Talks; Kuku; Pratilipi; Matrubharti; StoryWeaver;
Cogoport; Freightwalla; FreightTiger; Locus; Shipsy; FarEye; Ripplr; LetsTransport; TruckBhejo; Vahak;
Innovaccer; Practo; MediBuddy; Medikabazaar; Healthians; Redcliffe Labs; Orange Health; Thyrocare; Neuberg;
CureBay; Mojocare; Allo Health; Wysa; Amaha; MindPeers; Evolve; Ekincare; Visit Health; Plum; Loop Health;
Nova Benefits; Onsurity; Pazcare; Even; Galaxy Health; Turtlemint; InsuranceDekho; RenewBuy; Riskcovry;
Zype; Fello; Sahi; Dezerv; Wint Wealth; Grip Invest; Jiraaf; Stable Money; Upswing; Rario; FanCode;
Sportskeeda; Cricbuzz; Dream Capital; Junglee Games; A23; Nazara; Gameberry; SuperGaming; Octro; Moonfrog;
99Games; Lila Games; Hitwicket; Gametion; Kratos Studios; Ludo King; BeyondSkills; Physics Wallah; Adda247;
Doubtnut; Filo; Toppr; Vedantu; Seekho; Frontrow; Coursera; Spotle; Hirect; foundit; Naukri; iimjobs;
Instahyre; Cutshort; Wellfound; Uplers; Turing; Crossover; Toptal; Arc; Remote.com; Multiplier; Skuad;
Deel; Papaya Global; Darwinbox; greytHR; Zimyo; HROne; Qandle; sumHR; PeopleStrong; Ceipal; Leena AI;
Rocketlane; Hevo; Chargebee; Freshworks; Zoho; Wingify; Exotel; Mindtickle; Whatfix; Zluri; Sprinto;
CloudSEK; Cyble; Lucideus; Sequretek; Seclore; Appknox; Astra Security; Beagle Security; Safe Security;
Tessell; Atlan; Hasura; Postman; BrowserStack; Druva; Nutanix India; Rubrik India; Cohesity India; Couchbase;
Yugabyte; Sigmoid; Fractal Analytics; Tredence; LatentView; Course5 Intelligence; Gramener; Absolutdata
"""
CANDIDATES += """;
Composio; TrueFoundry; Portkey; Maxim AI; Smallest AI; Gnani.ai; Lyzr; Simplismart; Emergent; Reo.dev; Rocket;
Bolna; Krutrim; Giga; Nurix AI; Segwise; Neysa; E2E Networks; Pixis; Writesonic; Wadhwani AI; Rephrase.ai;
Nium; Airwallex; Rapyd; Thunes; Paddle; Calendly; Recharge; ShipBob; Velocity; Rakuten; ChargePoint; HackerRank;
HackerEarth; Zynga; Kwalee; Gameskraft; Probo; Pocket52; Head Digital Works; Cashify; Servify; Ola Krutrim;
Docquity; Innovaccer; Spry; Atomicwork; Lightning AI; Unify Apps; UnifyApps; Glean; Chronicle; Plivo; Exotel;
Zeta Suite; Fyle; Kapstan; Mercor; Juicebox; Assembly; Hyperface; Neokred; Kodo; Ezee; Fintech Labs;
Leap Scholar; Univest; Stockgro; Kite; Tickertape; Sensibull; Groww; Smallcase; Kuvera; Zerodha; Rupeezy;
CloudKeeper; Kubric; Ally; Nanonets; Docsumo; Rossum; Klippa; Instoried; Peppertype; Lemnisk; Zeotap;
Uniqode; Beaconstac; Postman; Hoppscotch; Keploy; Middleware; Kloudfuse; Last9; Ozone; Hyperswitch
"""
ALIASES = {
    "Ola": ["olacabs", "ola-electric", "olaelectric"], "Urban Company": ["urbancompany", "urban-company"],
    "Fi Money": ["fi", "epifi", "fimoney"], "Physics Wallah": ["physicswallah", "pw"], "Cult.fit": ["curefit", "cultfit"],
    "Digit Insurance": ["godigit", "digit"], "Park+": ["parkplus", "park-plus"], "Observe.AI": ["observeai", "observe-ai"],
    "Yellow.ai": ["yellowai", "yellow-ai"], "Kuku FM": ["kukufm", "kuku"], "Pocket FM": ["pocketfm"],
    "Dream Sports": ["dreamsports", "dream11"], "Hevo Data": ["hevodata", "hevo"], "Sarvam AI": ["sarvam", "sarvamai"],
    "Scrut Automation": ["scrut", "scrutautomation"], "Leena AI": ["leenaai", "leena"], "M2P Fintech": ["m2p", "m2pfintech"],
    "Ather Energy": ["atherenergy", "ather"], "Pine Labs": ["pinelabs"], "Cockroach Labs": ["cockroachlabs", "cockroach"],
    "Checkout.com": ["checkout", "checkoutcom"], "Culture Amp": ["cultureamp"], "Sumo Logic": ["sumologic"],
    "New Relic": ["newrelic"], "Tata 1mg": ["1mg", "tata1mg"], "BYJU'S": ["byjus"], "Great Learning": ["greatlearning"],
    "Course Hero": ["coursehero"], "VerSe Innovation": ["verse", "verseinnovation", "dailyhunt"],
    "Mu Sigma": ["musigma"], "Tiger Analytics": ["tigeranalytics"], "Qure.ai": ["qureai", "qure"],
    "Pristyn Care": ["pristyncare"], "Even Healthcare": ["even", "evenhealthcare"], "Eka Care": ["ekacare"],
    "Remote": ["remote", "remotecom"], "Booking": ["booking", "bookingcom"], "Sea": ["sea", "seagroup"],
    "Dyte": ["dyte"], "100ms": ["100ms"], "Twilio": ["twilio"], "Hotstar": ["hotstar", "disneyhotstar"],
    "Thoughtworks": ["thoughtworks"], "Zeta": ["zeta", "zetaglobal", "zeta-suite"], "Slice": ["slice", "sliceit"],
    "Jupiter": ["jupiter", "jupitermoney"], "Navi": ["navi", "navitechnologies"], "Plum": ["plum", "plumhq"],
    "Simpl": ["simpl", "getsimpl"], "Gnani.ai": ["gnani", "gnaniai"], "Smallest AI": ["smallest", "smallestai"],
    "Maxim AI": ["maxim", "maximai", "getmaxim"], "Reo.dev": ["reodev", "reo"], "Rocket": ["rocket", "rocketnew"],
    "Nurix AI": ["nurix", "nurixai"], "Rephrase.ai": ["rephrase", "rephraseai"], "Unify Apps": ["unifyapps"],
    "Leap Scholar": ["leapscholar", "leap"], "Lightning AI": ["lightningai", "lightning-ai"], "Jar": ["jar", "jarapp", "changejar"], "Fold": ["fold", "foldmoney"],
}


def slug_variants(name: str) -> list[str]:
    base = re.sub(r"[^a-z0-9 ]", "", name.lower().replace("+", "plus").replace("&", "and"))
    vs = [base.replace(" ", ""), base.replace(" ", "-")] + ALIASES.get(name, [])
    return list(dict.fromkeys(v for v in vs if v))


def probe(name: str, sess: requests.Session) -> list[dict]:
    """Try every slug variant on every ATS; return verified boards with India job counts."""
    found = []
    for a in ("greenhouse", "lever", "ashby"):
        for slug in slug_variants(name):
            status, data = ats.fetch_board(sess, a, slug, verify=True)
            time.sleep(0.2)
            if status == 200 and ats.board_exists(a, data):
                if a == "lever" or not data.get("jobs") or a == "ashby":
                    pass
                # verify endpoints omit descriptions; parse for India locations
                jobs = ats.PARSERS[a](data, name)
                n_all = len(data) if a == "lever" else len(data.get("jobs", []))
                found.append({"name": name, "ats": a, "board_slug": slug, "jobs_total": n_all,
                              "india_jobs": len(jobs),
                              "stack_india_jobs": sum(bool(STACK_RE.search(j["title"] or "")) for j in jobs)})
                break  # one slug per ATS is enough
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="companies.json")
    args = ap.parse_args()
    out = Path(args.out)
    existing = {(c["ats"], c["board_slug"]): c for c in json.loads(out.read_text())} if out.exists() else {}

    names = list(dict.fromkeys(n.strip() for n in CANDIDATES.replace("\n", " ").split(";") if n.strip()))
    search_by_name = {n: (a, s, q) for n, a, s, q in FROM_SEARCH}
    sess = requests.Session()
    results: list[dict] = []

    # boards from web search: verify the exact slug
    for n, a, s, q in FROM_SEARCH:
        status, data = ats.fetch_board(sess, a, s, verify=True)
        if status == 200 and ats.board_exists(a, data):
            jobs = ats.PARSERS[a](data, n)
            results.append({"name": n, "ats": a, "board_slug": s, "india_jobs": len(jobs),
                            "jobs_total": len(data) if a == "lever" else len(data.get("jobs", [])),
                            "stack_india_jobs": sum(bool(STACK_RE.search(j["title"] or "")) for j in jobs),
                            "discovered_via": f"web search: {q}"})
        time.sleep(0.3)

    # candidate list + India-source names: probe slugs (a few workers, each pausing between calls)
    india_src = {n: src for src, ns in INDIA_NAME_SOURCES.items() for n in ns}
    todo = list(dict.fromkeys([n for n in names if n not in search_by_name] + list(india_src)))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for name, found in zip(todo, ex.map(lambda n: probe(n, requests.Session()), todo)):
            for f in found:
                f["discovered_via"] = (india_src[name] + ", slug verified via API" if name in india_src
                                       else "candidate list (India-hiring companies), slug verified via API")
                f["india_based"] = name in india_src
                results.append(f)

    kept, seen = [], set()
    for r in sorted(results, key=lambda r: (-r["stack_india_jobs"], -r["india_jobs"], r["name"])):
        key = (r["ats"], r["board_slug"])
        if key in seen or (r["india_jobs"] == 0 and not r.get("india_based")):
            continue
        seen.add(key)
        prev = existing.get(key, {})
        kept.append({"name": r["name"], "ats": r["ats"], "board_slug": r["board_slug"],
                     "discovered_via": r["discovered_via"], "active": prev.get("active", True),
                     "india_jobs_at_bootstrap": r["india_jobs"], "stack_india_jobs_at_bootstrap": r["stack_india_jobs"],
                     "verified": time.strftime("%Y-%m-%d"),
                     # pruning: companies with kept_jobs_total == 0 30+ days after first_scanned are prune candidates
                     "first_scanned": prev.get("first_scanned", time.strftime("%Y-%m-%d")),
                     "kept_jobs_total": prev.get("kept_jobs_total", 0)})
    for key, c in existing.items():  # keep previously known boards (e.g. marked inactive)
        if key not in seen:
            c.setdefault("first_scanned", time.strftime("%Y-%m-%d"))
            c.setdefault("kept_jobs_total", 0)
            kept.append(c)
    # keep curated names / notes from the existing file
    by_key = {(c["ats"], c["board_slug"]): c for c in existing.values()}
    for c in kept:
        old = by_key.get((c["ats"], c["board_slug"]))
        if old:
            c["name"] = old.get("name", c["name"])
            if "note" in old:
                c["note"] = old["note"]
    out.write_text(json.dumps(kept, indent=2, ensure_ascii=False) + "\n")

    valid = {(r["ats"], r["board_slug"]) for r in results}
    print(f"candidates {len(names)} + India-source names {len({n for ns in INDIA_NAME_SOURCES.values() for n in ns})} "
          f"+ search slugs {len(FROM_SEARCH)}; valid boards {len(valid)}; kept {len(kept)} "
          f"({sum(c['india_jobs_at_bootstrap'] > 0 for c in kept)} with India jobs now) → {out}")
    for a in ("greenhouse", "lever", "ashby"):
        k = [c for c in kept if c["ats"] == a]
        print(f"  {a:<10} {len(k):>3} companies, {sum(c['india_jobs_at_bootstrap'] for c in k):>4} India jobs, "
              f"{sum(c['stack_india_jobs_at_bootstrap'] for c in k):>4} stack-matching titles")


if __name__ == "__main__":
    main()
