import json
import time
import contract as c
from datetime import datetime,timedelta
import time
import cloudscraper
import json

garden_contract_addr = "0x685BFDd3C2937744c13d7De0821c83191E3027FF"
lp_contract_addr = "0xa0feB3c81A36E885B6608DF7f0ff69dB97491b58"
wallet_public_addr = "0x361472B5784e83fBF779b015f75ea0722741f304"
dextool_lp_url = "https://www.dextools.io/chain-bsc/api/pair/search?p=0xa0feb3c81a36e885b6608df7f0ff69db97491b58"
loop_sleep_seconds = 0.5
margin_of_error = 0.1
seeds_per_day_per_plant = 86400
start_polling_threshold_in_seconds = 10

# load private key
wallet_private_key = open('key.txt', "r").readline()

# load abi
f = open('garden_abi.json')
garden_abi = json.load(f)

lp = open('drip_busd_abi.json')
lp_abi = json.load(lp)

# create contract
garden_contract = c.connect_to_contract(garden_contract_addr, garden_abi)
lp_contract = c.connect_to_contract(lp_contract_addr, lp_abi)

# cycle class
class cycleItem: 
    def __init__(self, id, type, minimumPlants): 
        self.id = id 
        self.type = type
        self.minimumPlants = minimumPlants

# cycle types are "plant" or "harvest"
cycle = [] 
cycle.append( cycleItem(1, "plant", 1.00) )
cycle.append( cycleItem(2, "plant", 1.00) )
cycle.append( cycleItem(3, "plant", 1.00) )
cycle.append( cycleItem(4, "plant", 1.00) )
cycle.append( cycleItem(5, "plant", 1.00) )
cycle.append( cycleItem(6, "plant", 1.00) )
cycle.append( cycleItem(7, "plant", 1.00) )
nextCycleId = 7

# methods
def total_liquidity():
    scraper = cloudscraper.create_scraper()
    rr = scraper.get(dextool_lp_url).text 
    yy = json.loads(rr)
    return yy[0]['liquidity']

def seeds_for_1_plant():
    seedsFor1Plant = garden_contract.functions.SEEDS_TO_GROW_1PLANT().call()
    return seedsFor1Plant

def available_seeds():
    return garden_contract.functions.getUserSeeds(wallet_public_addr).call()

def planted_plants():
    return garden_contract.functions.hatcheryPlants(wallet_public_addr).call()

def plant():
    txn = garden_contract.functions.plantSeeds(wallet_public_addr).buildTransaction(c.get_tx_options(wallet_public_addr, 500000))
    return c.send_txn(txn, wallet_private_key)

def harvest():
    txn = garden_contract.functions.sellSeeds().buildTransaction(c.get_tx_options(wallet_public_addr, 500000))
    return c.send_txn(txn, wallet_private_key)

def total_supply():
    total = lp_contract.functions.totalSupply().call()
    return total/1000000000000000000

def calc_plant_lp(seeds):
    total = garden_contract.functions.calculateSeedSell(seeds).call()
    return total/1000000000000000000

def buildTimer(t):
    mins, secs = divmod(int(t), 60)
    hours, mins = divmod(int(mins), 60)
    timer = '{:02d} hours, {:02d} minutes, {:02d} seconds'.format(hours, mins, secs)
    return timer

def getNextPlantingDate(t):
    mins, secs = divmod(int(t), 60)
    hours, mins = divmod(int(mins), 60)
    nextPlantAt = datetime.today() + timedelta(hours=hours,minutes=mins,seconds=secs)
    timestampStr = nextPlantAt.strftime("[%d-%b-%Y (%H:%M:%S)]")
    return timestampStr

def countdown(t):
    while t:
        print(f"Next poll in: {buildTimer(t)}", end="\r")
        time.sleep(1)
        t -= 1

def findCycleMinimumPlants(cycleId):
    for x in cycle:
        if x.id == cycleId:
            return x.minimumPlants
            break
        else:
            x = None

def findCycleType(cycleId):
    for x in cycle:
        if x.id == cycleId:
            return x.type
            break
        else:
            x = None

def getNextCycleId(currentCycleId):
    cycleLength = len(cycle)
    if currentCycleId == cycleLength:
        return 1
    else:
        return currentCycleId + 1

# create infinate loop that checks contract every set sleep time
nextCycleType = findCycleType(nextCycleId)

def itterate(nextCycleId, nextCycleType):
    seedsFor1Plant = seeds_for_1_plant()
    available = available_seeds()
    plantedPlants = planted_plants()
    availablePlants = available / seedsFor1Plant

    plantLpValue = calc_plant_lp(seedsFor1Plant)

    cycleMinimumPlants = findCycleMinimumPlants(nextCycleId)

    plantsNeededForPlanting = (cycleMinimumPlants + margin_of_error) - availablePlants
    seedsNeededForPlanting = plantsNeededForPlanting * seedsFor1Plant
    
    seedsPerDay = plantedPlants * seeds_per_day_per_plant
    plantsPerDay = seedsPerDay/seedsFor1Plant
    
    daysUntilPlanting = seedsNeededForPlanting / seedsPerDay
    hoursUntilPlanting = daysUntilPlanting * 24 
    secondsUntilPlanting = hoursUntilPlanting * 60 * 60

    totalSupply = total_supply()
    totalLiquidityValue = total_liquidity()

    lpValuePerDay = (float(totalLiquidityValue)/float(totalSupply))*plantLpValue*plantsPerDay

    dateTimeObj = datetime.now()
    timestampStr = dateTimeObj.strftime("[%d-%b-%Y (%H:%M:%S)]")

    sleep = loop_sleep_seconds 
    
    print("********** STATS *******")
    print(f"{timestampStr} Next cycle type: {nextCycleType}")
    print(f"{timestampStr} LP daily value: {(lpValuePerDay):.3f}")
    print(f"{timestampStr} Plants per day: {(seedsPerDay/seedsFor1Plant):.3f}")
    print(f"{timestampStr} Planted plants: {plantedPlants:.3f}")
    print(f"{timestampStr} Available plants: {availablePlants:.3f}")
    print(f"{timestampStr} Margin of error: {margin_of_error:.3f}")
    print(f"{timestampStr} Minimum plants to plant: {cycleMinimumPlants:.3f}")
    print(f"{timestampStr} Plants needed before planting: {plantsNeededForPlanting:.3f}")
    print(f"{timestampStr} Until next planting: {buildTimer(secondsUntilPlanting)}")
    print(f"{timestampStr} Next planting at: {getNextPlantingDate(secondsUntilPlanting)}")
    print(f"{timestampStr} Start polling each {(loop_sleep_seconds / 60):.2f} minute {(start_polling_threshold_in_seconds / 60):.3f} minutes before next planting")
    print("************************")

    if secondsUntilPlanting > start_polling_threshold_in_seconds:
        sleep = secondsUntilPlanting - start_polling_threshold_in_seconds
            
    if availablePlants >= cycleMinimumPlants: # and availablePlants < (cycleMinimumPlants + margin_of_error):
        if nextCycleType == "plant":
            plant()
        if nextCycleType == "harvest":
            harvest()
        
        if nextCycleType == "plant":
            print("********** PLANTED *******")
            print(f"{timestampStr} Added {availablePlants:.2f} plants to the garden!")
        if nextCycleType == "harvest":
            print("********** HARVESTED *****")
            print(f"{timestampStr} Sold {availablePlants:.2f} plants!")

        nextCycleId = getNextCycleId(nextCycleId)
        nextCycleType = findCycleType(nextCycleId)
        print(f"{timestampStr} Next cycleId is: {nextCycleId}")
        print(f"{timestampStr} Next cycle type will be: {nextCycleType}")
        print("**************************")

    countdown(int(sleep))

retryCount = 0
while True:
    try: 
        if retryCount < 5:
            itterate(nextCycleId, nextCycleType)  
    except Exception as e:
        print("[EXCEPTION] Something went wrong! Message:")
        print(f"[EXCEPTION] {e}")
        retryCount = retryCount + 1
        if retryCount < 5:
            itterate(nextCycleId, nextCycleType)
        print(f"[EXCEPTION] Retrying! (retryCount: {retryCount})")
