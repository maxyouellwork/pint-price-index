#!/usr/bin/env python3
"""
Process raw Wetherspoons API data into clean spoons.json for the app.
Filters to beer/lager/cider only (ABV > 0), computes regional averages,
and generates leaderboards.
"""
import json, sys, os

RAW_FILE = "/tmp/spoons_prices.json"
OUTPUT = os.path.join(os.path.dirname(__file__), "spoons.json")

# Beer categories to include (case-insensitive substring match)
BEER_CATS = ['lager', 'beer', 'stout', 'craft', 'cider', 'ale', 'world beer']

def is_beer(drink):
    """Filter: only include alcoholic draught beer/lager/cider."""
    cat = drink.get('cat', '').lower()
    abv = drink.get('abv', '')

    # Must have ABV > 0
    try:
        if float(abv) <= 0:
            return False
    except (ValueError, TypeError):
        # If no ABV, check category
        if not any(bc in cat for bc in BEER_CATS):
            return False

    # Exclude obvious non-beer
    name = drink.get('name', '').lower()
    exclude = ['cordial', 'juice', 'water', 'coffee', 'tea', 'pepsi', 'cola', 'lemonade', 'j2o', 'appletiser', 'ginger']
    if any(e in name for e in exclude):
        return False

    return True

def main():
    with open(RAW_FILE) as f:
        raw = json.load(f)

    pubs = raw.get('pubs', [])
    print(f"Raw data: {len(pubs)} pubs")

    clean_pubs = []

    for pub in pubs:
        # Filter to beer only
        beers = [d for d in pub.get('drinks', []) if is_beer(d)]
        if not beers:
            continue

        # Get pint prices of in-stock beers
        prices = [d['pint'] for d in beers if d.get('pint') and not d.get('oos')]
        if not prices:
            continue

        avg = round(sum(prices) / len(prices), 2)
        cheapest = min(prices)
        most_exp = max(prices)
        cheapest_name = next((d['name'] for d in beers if d['pint'] == cheapest and not d.get('oos')), None)

        # Simplified drink list (deduplicated, just name, abv, price)
        seen = set()
        drink_list = []
        for d in beers:
            if d.get('pint') and not d.get('oos'):
                key = (d['name'], d['pint'])
                if key not in seen:
                    seen.add(key)
                    drink_list.append({
                        'name': d['name'],
                        'price': d['pint'],
                        'abv': d.get('abv', ''),
                    })
        drink_list.sort(key=lambda x: x['price'])

        clean_pubs.append({
            'name': pub['name'],
            'ref': pub.get('ref'),
            'town': pub['town'],
            'county': pub.get('county', ''),
            'postcode': pub.get('postcode', ''),
            'lat': pub.get('lat'),
            'lon': pub.get('lon'),
            'avg': avg,
            'min': cheapest,
            'max': most_exp,
            'cheapest': cheapest_name,
            'beers': len(drink_list),
            'drinks': drink_list
        })

    print(f"Clean data: {len(clean_pubs)} pubs with beer prices")

    # Sort by average price
    clean_pubs.sort(key=lambda x: x['avg'])

    # Stats
    all_avgs = [p['avg'] for p in clean_pubs]
    all_mins = [p['min'] for p in clean_pubs]
    national_avg = round(sum(all_avgs) / len(all_avgs), 2)

    # Regional averages (group by county, then roll up to regions)
    REGION_MAP = {
        # London boroughs (all 32 + City)
        'Camden': 'London', 'City of London': 'London', 'Farringdon': 'London',
        'Hackney': 'London', 'Hammersmith': 'London', 'Hammersmith & Fulham': 'London',
        'Islington': 'London', 'Lambeth': 'London', 'Lewisham': 'London',
        'Southwark': 'London', 'Tower Hamlets': 'London', 'Wandsworth': 'London',
        'Westminster': 'London', 'London': 'London', 'Middlesex': 'London',
        'Hillingdon': 'London', 'Hounslow': 'London', 'Brent': 'London',
        'Barnet': 'London', 'Enfield': 'London', 'Haringey': 'London',
        'Waltham Forest': 'London', 'Redbridge': 'London', 'Newham': 'London',
        'Barking': 'London', 'Barking and Dagenham': 'London',
        'Havering': 'London', 'Bexley': 'London', 'Bromley': 'London',
        'Croydon': 'London', 'Sutton': 'London', 'Merton': 'London',
        'Kingston': 'London', 'Kingston upon Thames': 'London',
        'Richmond': 'London', 'Richmond upon Thames': 'London',
        'Ealing': 'London', 'Greenwich': 'London', 'Woolwich': 'London',
        'Harrow': 'London', 'Kensington and Chelsea': 'London',
        'Kensington': 'London', 'Chelsea': 'London',
        # Scotland
        'Edinburgh': 'Scotland', 'Glasgow': 'Scotland', 'Lanarkshire': 'Scotland',
        'South Lanarkshire': 'Scotland', 'North Lanarkshire': 'Scotland',
        'Fife': 'Scotland', 'Renfrewshire': 'Scotland', 'East Renfrewshire': 'Scotland',
        'Ayrshire': 'Scotland', 'North Ayrshire': 'Scotland', 'East Ayrshire': 'Scotland',
        'South Ayrshire': 'Scotland',
        'Inverness-shire': 'Scotland', 'Highland': 'Scotland', 'Highlands': 'Scotland',
        'Angus': 'Scotland', 'Aberdeenshire': 'Scotland', 'Aberdeen': 'Scotland',
        'Perth and Kinross': 'Scotland', 'Perth': 'Scotland',
        'Dundee': 'Scotland', 'Stirling': 'Scotland',
        'Dunbartonshire': 'Scotland', 'West Dunbartonshire': 'Scotland',
        'East Dunbartonshire': 'Scotland',
        'Borders': 'Scotland', 'Scottish Borders': 'Scotland',
        'Falkirk': 'Scotland', 'Clackmannanshire': 'Scotland',
        'Midlothian': 'Scotland', 'East Lothian': 'Scotland', 'West Lothian': 'Scotland',
        # Wales
        'Glamorgan': 'Wales', 'Vale of Glamorgan': 'Wales',
        'Gwent': 'Wales', 'Dyfed': 'Wales', 'Gwynedd': 'Wales',
        'Clwyd': 'Wales', 'Powys': 'Wales', 'Cardiff': 'Wales', 'Swansea': 'Wales',
        'Carmarthenshire': 'Wales', 'Pembrokeshire': 'Wales', 'Ceredigion': 'Wales',
        'Wrexham': 'Wales', 'Conwy': 'Wales', 'Bridgend': 'Wales',
        'Blaenau Gwent': 'Wales', 'Caerphilly': 'Wales', 'Monmouthshire': 'Wales',
        'Rhondda Cynon Taf': 'Wales', 'Neath Port Talbot': 'Wales',
        'Torfaen': 'Wales', 'Newport': 'Wales', 'Flintshire': 'Wales',
        'Denbighshire': 'Wales', 'Anglesey': 'Wales', 'Isle of Anglesey': 'Wales',
        'Merthyr Tydfil': 'Wales',
        # Northern Ireland
        'County Antrim': 'Northern Ireland', 'County Down': 'Northern Ireland',
        'County Armagh': 'Northern Ireland', 'County Tyrone': 'Northern Ireland',
        'County Londonderry': 'Northern Ireland', 'County Fermanagh': 'Northern Ireland',
        'Belfast': 'Northern Ireland', 'Antrim': 'Northern Ireland',
        # Ireland (Republic)
        'County Dublin': 'Ireland', 'Dublin': 'Ireland',
        'County Cork': 'Ireland', 'County Galway': 'Ireland',
        'County Limerick': 'Ireland', 'County Waterford': 'Ireland',
        'County Wexford': 'Ireland', 'County Kildare': 'Ireland',
        # South East
        'Kent': 'South East', 'Surrey': 'South East', 'Sussex': 'South East',
        'East Sussex': 'South East', 'West Sussex': 'South East',
        'Hampshire': 'South East', 'Berkshire': 'South East', 'Oxfordshire': 'South East',
        'Buckinghamshire': 'South East', 'Hertfordshire': 'South East',
        'Essex': 'South East', 'Bedfordshire': 'South East',
        # South West
        'Devon': 'South West', 'Cornwall': 'South West', 'Somerset': 'South West',
        'Dorset': 'South West', 'Wiltshire': 'South West', 'Gloucestershire': 'South West',
        'Bristol': 'South West', 'Bath': 'South West',
        'Bath and North East Somerset': 'South West',
        # East
        'Norfolk': 'East of England', 'Suffolk': 'East of England',
        'Cambridgeshire': 'East of England', 'Northamptonshire': 'East of England',
        # Midlands
        'West Midlands': 'Midlands', 'Warwickshire': 'Midlands',
        'Staffordshire': 'Midlands', 'Worcestershire': 'Midlands',
        'Shropshire': 'Midlands', 'Herefordshire': 'Midlands',
        'Derbyshire': 'Midlands', 'Nottinghamshire': 'Midlands',
        'Leicestershire': 'Midlands', 'Lincolnshire': 'Midlands',
        'Rutland': 'Midlands', 'Birmingham': 'Midlands',
        'Coventry': 'Midlands', 'Solihull': 'Midlands',
        # North West
        'Greater Manchester': 'North West', 'Lancashire': 'North West',
        'Merseyside': 'North West', 'Cheshire': 'North West', 'Cumbria': 'North West',
        'Manchester': 'North West', 'Liverpool': 'North West',
        'Stockport': 'North West', 'Wigan': 'North West', 'Bolton': 'North West',
        # North East
        'Tyne and Wear': 'North East', 'County Durham': 'North East',
        'Northumberland': 'North East', 'Cleveland': 'North East',
        'Newcastle upon Tyne': 'North East', 'Sunderland': 'North East',
        'Gateshead': 'North East', 'Durham': 'North East',
        'Teesside': 'North East', 'Middlesbrough': 'North East',
        # Yorkshire
        'South Yorkshire': 'Yorkshire', 'West Yorkshire': 'Yorkshire',
        'North Yorkshire': 'Yorkshire', 'East Riding of Yorkshire': 'Yorkshire',
        'Sheffield': 'Yorkshire', 'Leeds': 'Yorkshire', 'York': 'Yorkshire',
        'Bradford': 'Yorkshire', 'Hull': 'Yorkshire',
        'Kingston Upon Hull': 'Yorkshire', 'Wakefield': 'Yorkshire',
        'Calderdale': 'Yorkshire', 'Barnsley': 'Yorkshire', 'Doncaster': 'Yorkshire',
        'Rotherham': 'Yorkshire', 'Kirklees': 'Yorkshire',
        # Additional Scotland
        'Argyll and Bute': 'Scotland', 'Dundee City': 'Scotland',
        'Dumfries and Galloway': 'Scotland', 'Moray': 'Scotland',
        'Inverclyde': 'Scotland',
        # Additional North East
        'Stockton-on-Tees': 'North East',
        # Additional Wales
        'Rhondda Cynon Taff': 'Wales',
        # Additional Midlands
        'Telford & Wrekin': 'Midlands',
        # Additional South West
        'South Gloucestershire': 'South West',
        # Additional South East
        'Isle of Wight': 'South East',
        # North West (trailing space variant)
        'Greater Manchester ': 'North West',
    }

    regions = {}
    for p in clean_pubs:
        county = p.get('county', '').strip()
        region = REGION_MAP.get(county, county)
        regions.setdefault(region, []).append(p['avg'])

    regional = []
    for name, prices in regions.items():
        if len(prices) >= 2:  # Need at least 2 pubs for meaningful average
            regional.append({
                'name': name,
                'avg': round(sum(prices) / len(prices), 2),
                'pubs': len(prices),
                'min': round(min(prices), 2),
                'max': round(max(prices), 2),
            })
    regional.sort(key=lambda x: -x['avg'])

    # Build output
    output = {
        'meta': {
            'source': 'Wetherspoons JDW Apps API',
            'fetchDate': raw.get('meta', {}).get('fetchDate', ''),
            'totalPubs': len(clean_pubs),
            'totalBeers': sum(p['beers'] for p in clean_pubs),
            'avgPint': national_avg,
            'cheapestPint': min(all_mins),
            'mostExpensivePint': max(p['max'] for p in clean_pubs),
        },
        'regional': regional,
        'cheapest': [{
            'name': p['name'], 'town': p['town'], 'postcode': p['postcode'],
            'avg': p['avg'], 'min': p['min'], 'cheapest': p['cheapest'],
            'lat': p['lat'], 'lon': p['lon']
        } for p in clean_pubs[:20]],
        'priciest': [{
            'name': p['name'], 'town': p['town'], 'postcode': p['postcode'],
            'avg': p['avg'], 'max': p['max'],
            'lat': p['lat'], 'lon': p['lon']
        } for p in clean_pubs[-20:][::-1]],
        'pubs': [{
            'name': p['name'], 'town': p['town'], 'county': p['county'],
            'postcode': p['postcode'], 'lat': p['lat'], 'lon': p['lon'],
            'avg': p['avg'], 'min': p['min'], 'max': p['max'],
            'cheapest': p['cheapest'], 'beers': p['beers'],
            'drinks': p['drinks'][:10]  # Top 10 cheapest drinks per pub
        } for p in clean_pubs]
    }

    with open(OUTPUT, 'w') as f:
        json.dump(output, f)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\nOutput: {OUTPUT} ({size_kb:.0f} KB)")
    print(f"National avg pint: £{national_avg}")
    print(f"Cheapest: £{min(all_mins)} at {clean_pubs[0]['name']} ({clean_pubs[0]['town']})")
    print(f"Most expensive avg: £{clean_pubs[-1]['avg']} at {clean_pubs[-1]['name']} ({clean_pubs[-1]['town']})")
    print(f"\nRegional averages:")
    for r in regional[:10]:
        print(f"  {r['name']}: £{r['avg']} ({r['pubs']} pubs)")

if __name__ == '__main__':
    main()
