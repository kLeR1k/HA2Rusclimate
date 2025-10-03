# HA2Rusclimate
Трансляция температуры из Home Assistant для "умных" конвекторов Rusclimate/Hommyn (Ballu, Electrolux)
Создание "виртуального" датчика температуры на базе Home Assistant + подписка конвектора на "виртуальный" датчик температуры.

Для понимания того, как работает штатная подписка конвектора на термометр из экосистемы Rusclimate/Hommyn:
- Термометр имеет свой уникальный MAC-адрес
- При создании подписки конвектора на внешний термометр, MQTT-топик конвектора `rusclimate/device_id/mac/state/subscriptions` в первых 12 символах в RAW-формате содержит MAC-адрес термометра
- Конвектор периодически отправляет широковещательный запрос mDNS в своей Wi-fi сети (отсюда требование Rusclimate/Hommyn - устройства должны находиться в одной сети т.к. mDNS пакеты за пределы сети по умолчанию не передаются)
- Все Wi-fi устройства Rusclimate начинают ему отвечать пакетами того же протокола о своём состоянии (в том числе со своим MAC-адресом и текущем состоянии сенсоров)
- Конвектор получает каждый из этих пакетов, но оставляет себе только пакет от устройства с MAC-адресом из `rusclimate/device_id/mac/state/subscriptions`, и использует из него значение сенсора текущей температуры для своей PID-регулировки

## Пререквизиты
1. Конвектор уже общается с вашим локальным MQTT-брокером, а не с облаком Rusclimate
2. В HA установлены:
   - Интеграция [Local IP](https://www.home-assistant.io/integrations/local_ip)
   - Интеграция в HACS [Pyscript](https://github.com/custom-components/pyscript)
  
## Способ использования
1. В configuration.yaml для вашего конвектора добавить 2 сущности:
MAC-адрес "виртуального" датчика
```
  - sensor:
      device:
         name: Ballu Heater Livingroom
         identifiers: ["ballu-heater-**092031d745088170c971d516903256b1**"]
      name: Ballu HA translation Mac
      unique_id: "ballu_heater_mac_56b1"
      state_topic: rusclimate/**46**/**092031d745088170c971d516903256b1**/state/mac
      value_template: >
        {{ "aaaa" + value[4:] }}
```



```
  - select:
      device:
         name: Ballu Heater Livingroom
         identifiers: ["ballu-heater-092031d745088170c971d516903256b1"]
      name: Ballu Subscriptions
      unique_id: "ballu_subscriptions_56b1"
      state_topic: rusclimate/46/092031d745088170c971d516903256b1/state/subscriptions
      command_topic: rusclimate/46/092031d745088170c971d516903256b1/control/subscriptions
      encoding: ""
      options:
        - "No subscription"
        - "HA translation"
        - "Unknown device"
      value_template: >
        {% set dev_subscription_mac = value.hex()[0:12] %}
        {{ iif(dev_subscription_mac == "000000000000", "No subscription", iif ( dev_subscription_mac == states('sensor.ballu_heater_livingroom_ballu_ha_translation_mac'), "HA translation", "Unknown device" ) ) }}
      command_template: >
        {% set no_subscription_mac = "000000000000000000000000" | from_hex %}
        {% set ha_subscription_mac = ( states('sensor.ballu_heater_livingroom_ballu_ha_translation_mac') + "000000000000" ) | from_hex %}
        {% set second_part = "000000000000000000000000000000" | from_hex %}
        {% set separator = '.'.encode("UTF-8")  %}
        {{ iif( value == "No subscription", no_subscription_mac + separator + second_part , iif( value == "HA translation", ha_subscription_mac + separator + second_part, "" ))  }}
```
