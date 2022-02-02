import os
import redis
import logging
logging.basicConfig(level=logging.INFO)

from oscar_lib import OscarClient, Station

wigos_ids = os.getenv('STATIONS',"").split(",")

client = OscarClient()
r = redis.Redis(host="redis")

for wid in wigos_ids:

    logging.info(f"processing {wid}")
    
    try:
    
        station = Station( client.load_station(wigos_id=wid) )
        # FIXME
        
        name = station.get_name()
        location = station.get_location(active_only=True)
        wigos_id_components = station.get_wigos_ids(primary=True).split("-")
        
        json_info = { 
            "name" : name,
            "location" : { k:float(v) for (k,v) in location.items() },
            "wigosId" : {
                "wid_series": wigos_id_components[0], 
                "wid_issuer": wigos_id_components[1],
                "wid_issue_number": wigos_id_components[2],
                "wid_local": wigos_id_components[3]
            }
        }

        logging.info("storing info in redis")    
        r.json().set(wid, "." , json_info)
        logging.info(f"ok {wid}")
        
    except Exception as e:
        logging.error(f"error during processing {wid}")
    
logging.info("done")