import socket
import hashlib
from homeassistant.components import zeroconf
from zeroconf.asyncio import AsyncServiceInfo

def mac_to_key(mac: str) -> str:
    return hashlib.sha256(mac.encode()).hexdigest()

service_type = "_syncleo._udp.local."

def get_service_name( mac: str ) -> str:
    return mac+'.'+service_type

def register_service(ip, port, mac_entity_id, temp_entity_id):
    aiozc = zeroconf.async_get_async_instance(hass)
    mac = state.get(mac_entity_id)
    service_name = get_service_name(mac)
    info = AsyncServiceInfo(
        server=service_name,
        type_= service_type,
        name=service_name,
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={
            '000000000000.temperature': round(float(state.get(temp_entity_id)), 2),
            '000000000000.target_temp':'25.0',
            'public':mac_to_key(mac),
            'curve':'29',
            'vendor':'RusClimate',
            'basetype':'46',
            'devtype':'46',
            'firmware':'1.43',
            'protocol':'3',
            'macaddr':":".join([mac[i:i+2] for i in range(0, 12, 2)])
        }
    )
    
    if await aiozc.async_get_service_info(service_type, service_name) == None:
        aiozc.async_register_service(info)
    else:
        aiozc.async_update_service(info)

@service
def ha_to_rusclimate_advertise(mac_entity_id, temp_entity_id):
    register_service(sensor.local_ip, 41122, mac_entity_id, temp_entity_id)
    
@service    
def stop_ha_to_rusclimate_advertise(mac_entity_id):
    aiozc = zeroconf.async_get_async_instance(hass)
    info = await aiozc.async_get_service_info(service_type, get_service_name(state.get(mac_entity_id)))
    if info != None:
        await aiozc.async_unregister_service(info)