![photo_2025-10-03_18-22-55](https://github.com/user-attachments/assets/de658f2f-4b3b-4b50-bb7e-c0cab4886bce)<img width="1280" height="559" alt="image" src="https://github.com/user-attachments/assets/31e5cc86-3ef7-45f6-9b6f-69d878eec2b2" /># HA2Rusclimate
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
### В configuration.yaml в разделе mqtt для вашего конвектора добавить 2 сущности:
С заменой соответствующих значений, описанных ниже.
В результате:
1. Определяется MAC-адрес "виртуального" термометра (вместо первых 4 символов MAC-адреса конвектора используется `aaaa`)
2. Появляется возможность создать подписку для конвектора на "виртуальный" термометр
#### MAC-адрес "виртуального" датчика
```
  - sensor:
      device:
         name: Ballu Heater Livingroom
         identifiers: ["ballu-heater-092031d745088170c971d516903256b1"]
      name: Ballu HA translation Mac
      unique_id: "ballu_heater_mac_56b1"
      state_topic: rusclimate/46/092031d745088170c971d516903256b1/state/mac
      value_template: >
        {{ "aaaa" + value[4:] }}
```

#### Статус/управление подпиской:
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
Где:

<img width="320" height="90" alt="image" src="https://github.com/user-attachments/assets/e3b45949-6f19-4276-8b56-a8222b23e74f" />

1. `46` - device_id
2. `092031d745088170c971d516903256b1` - mac из ветки топиков rusclimate (в вашем случае будет отличаться)
3. `ballu_heater_livingroom_ballu_ha_translation_mac` - имя сенсора из раздела `MAC-адрес "виртуального" датчика` (определяется как конкатенация `device-name` + `name` в нижнем регистре с разделителем `_`)

После изменения configuration.yaml необходима перезагрузка интеграции mqtt.

### Сохранить скрипт в Home Assistant
[Скрипт](rusclimate_to_ha_subsctription.py) необходим для того, чтобы "виртуальный" термометр отвечал на mDNS-запросы конвектора о своём состоянии.
Обычно это папка pyscript в директории Home Assistant (если нет после установки интеграции - создать вручную).
После сохранения файла необходим перезапуск интеграции.

Скрипт в том числе содержит определения для 2 сервисов:
1. `ha_to_rusclimate_advertise` - обновляет текущее состояние "виртуального" термометра (на вход подаётся: `mac_entity_id` - имя сенсора из раздела `MAC-адрес "виртуального" датчика`; `temp_entity_id` - имя сенсора, состояние которого транслируется через "виртуальный" термометр)
2. `stop_ha_to_rusclimate_advertise` - останавливает ответы "виртуального" термометра конвектору на случай отмены подписки


### Создать автоматизации в Home Assistant
#### Для "обновления" текущего состояния "виртуального" термометра
Как пример:
```
alias: Гостинная. Конвектор. Проброс температуры
description: ""
triggers:
  - trigger: state
    entity_id:
      - select.ballu_heater_livingroom_ballu_subscriptions
    to: HA translation
  - trigger: state
    entity_id:
      - sensor.temperatura_gostinnaia_sredniaia
conditions:
  - condition: state
    entity_id: select.ballu_heater_livingroom_ballu_subscriptions
    state: HA translation
actions:
  - action: pyscript.ha_to_rusclimate_advertise
    data:
      mac_entity_id: sensor.ballu_heater_livingroom_ballu_ha_translation_mac
      temp_entity_id: sensor.temperatura_gostinnaia_sredniaia
mode: single
```
#### Для остановки ответов "виртуального" термометра
На случай, если подписка будет отменена, чтобы не засорять эфир
```
alias: Гостинная. Конвектор. Остановить проброс температуры
description: ""
triggers:
  - trigger: state
    entity_id:
      - select.ballu_heater_livingroom_ballu_subscriptions
    to: No subscription
  - trigger: state
    entity_id:
      - select.ballu_heater_livingroom_ballu_subscriptions
    to: Unknown device
conditions: []
actions:
  - action: pyscript.stop_ha_to_rusclimate_advertise
    data:
      mac_entity_id: sensor.ballu_heater_livingroom_ballu_ha_translation_mac
mode: single
```


## Результат
### С управлением на основе показаний встроенного датчика
Графики сверху внизу:
1. Гистограмма текущей мощности конвектора
2. Показания штатного датчика + установленная температура
3. Средние показания температуры (виртуального сенсора) на основе 2-х термометров в комнате площадью 12 м2
![photo_2025-10-03_18-22-45](https://github.com/user-attachments/assets/c037b8d4-997c-4b16-a967-528e494da1e1)

В итоге средние показания температуры "рваные" + 5 полных циклов нагрева/охлаждения за 11 часов

### С управлением на основе "виртуального" термометра
Графики сверху внизу:
1. Гистограмма текущей мощности конвектора
2. Показания штатного датчика + установленная температура
3. Средние показания температуры (виртуального сенсора) на основе 2-х термометров в комнате площадью 12 м2
![photo_2025-10-03_18-22-55](https://github.com/user-attachments/assets/7db09c9d-d311-4072-a4bb-f3843afbbe40)

В итоге средние показания температуры сглаженные + всего 3 полных цикла нагрева/охлаждения за 11 часов и в целом меньшее кол-во переключений текущей мощности конвектора

## Post-scriptum
Честно говоря не до конца устраивает текущий результат по работе конвектора (использую `Ballu Evolution Transformer BEC/EVU-1500`) - как видно по графикам идёт перегрев на 2 градуса относительно установленной целевой температуры, но температура действительно не опускается ниже целевой. И в ясную погоду приходится целевую температуру занижать (иначе перегрев получается ещё больше видимо из-за медленного PID), а в пасмурную/тёмное время суток увеличивать.
Пока реализация не оттестирована, но если есть желание - можно использовать.



