# Judge validation: label 30 answers

For each answer, decide whether it is **correct** (states the expected fact, no wrong figure) or **incorrect**. Ignore style. Reply in chat with the numbers you think are incorrect, e.g. "incorrect: 4, 17"; everything else is taken as correct.

## 1. `sn01`

**Q:** What's the maximum input voltage on the VIN pad / DC jack of the Arduino UNO R4 WiFi?

**Expected:** 24 V (max)  
**Datasheet:** ABX00087 p.[7]: "Input voltage from VIN pad / DC Jack"

**Agent answered:** The maximum input voltage on the VIN pad / DC jack of the Arduino UNO R4 WiFi is 24 V.

## 2. `sn04`

**Q:** What's the typical VIN voltage for the UNO R4 Minima?

**Expected:** 7.0 V (typ)  
**Datasheet:** ABX00080 p.[6]: "Input voltage from VIN pad / DC Jack"

**Agent answered:** The UNO R4 Minima's typical VIN input voltage is 7.0 V.

## 3. `sn07`

**Q:** What's the minimum VIN / DC jack input voltage for the Mega 2560 Rev3?

**Expected:** 7 V (min)  
**Datasheet:** A000067 p.[5]: "Input voltage from VIN pad / DC Jack"

**Agent answered:** The minimum VIN / DC jack input voltage for the Arduino Mega 2560 Rev3 is 7 V.

## 4. `sn10`

**Q:** What's the maximum voltage I can put on the USB connector of the MKR WiFi 1010?

**Expected:** 5.5 V (max)  
**Datasheet:** ABX00023 p.[7]: "Maximum input voltage from USB connector"

**Agent answered:** The maximum input voltage from the USB connector on the MKR WiFi 1010 is 5.5 V.

## 5. `sn13`

**Q:** What's the minimum input high-level voltage for the MKR WAN 1310's I/O?

**Expected:** 1.815 V (min)  
**Datasheet:** ABX00029 p.[14]: "Input high-level voltage"

**Agent answered:** The minimum input high-level voltage (VIH) for the MKR WAN 1310 is 1.815 V.

## 6. `sn16`

**Q:** What is the maximum power consumption of the Portenta Max Carrier?

**Expected:** 5000 mW (max)  
**Datasheet:** ABX00043 p.[6]: "Maximum Power Consumption"

**Agent answered:** The Portenta Max Carrier's maximum power consumption (PMax) is 5000 mW.

## 7. `sn19`

**Q:** How much power does the Portenta X8 draw running a busy loop?

**Expected:** 2350 mW (typ)  
**Datasheet:** ABX00049 p.[8]: "Power consumption with busy loop"

**Agent answered:** The Portenta X8's typical power consumption with a busy loop is 2350 mW.

## 8. `sn22`

**Q:** What's the minimum VIN for the Nicla Sense ME?

**Expected:** 3.5 V (min)  
**Datasheet:** ABX00050 p.[7]: "Input voltage from VIN pad"

**Agent answered:** The Nicla Sense ME's minimum VIN is 3.5 V.

## 9. `sn25`

**Q:** What's the maximum battery input voltage for the Nicla Vision?

**Expected:** 4.7 V (max)  
**Datasheet:** ABX00051 p.[8]: "Input voltage from battery"

**Agent answered:** The Nicla Vision's maximum battery input voltage (VBATT) is 4.7 V.

## 10. `sn28`

**Q:** What's the maximum USB input voltage of the Nano RP2040 Connect?

**Expected:** 5.25 V (max)  
**Datasheet:** ABX00053 p.[7]: "Input voltage from USB connector"

**Agent answered:** The Nano RP2040 Connect's maximum USB input voltage (VUSB) is 5.25 V.

## 11. `sn31`

**Q:** What's the highest VIN voltage the GIGA R1 WiFi supports?

**Expected:** 32 V (max)  
**Datasheet:** ABX00063 p.[7]: "Input voltage from VIN pad"

**Agent answered:** I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions.

## 12. `sn34`

**Q:** What is the Portenta C33's current consumption in deep sleep mode?

**Expected:** 86 µA (typ)  
**Datasheet:** ABX00074 p.[9]: "Deep Sleep Mode Current Consumption"

**Agent answered:** The Portenta C33's deep sleep mode current consumption is typically 86 µA (minimum and maximum not stated).

## 13. `sc01`

**Q:** On the Nano RP2040 Connect, what's the minimum output high voltage when sourcing 8 mA?

**Expected:** 2.7 V (min)  
**Datasheet:** ABX00053 p.[7]: "Output high voltage, 8 mA"

**Agent answered:** The minimum output high voltage at 8 mA is 2.7 V.

## 14. `sc04`

**Q:** What's the maximum output high voltage on the Portenta X8 at 8 mA?

**Expected:** 3.3 V (max)  
**Datasheet:** ABX00049 p.[8]: "Output high voltage, 8 mA"

**Agent answered:** The Portenta X8's maximum output high voltage at 8 mA is 3.3 V.

## 15. `sc07`

**Q:** What's the Nicla Vision's average current while it's capturing images?

**Expected:** 105 mA (typ)  
**Datasheet:** ABX00051 p.[8]: "Average current consumption during image capture"

**Agent answered:** The Nicla Vision's typical average current consumption during image capture is 105 mA.

## 16. `sc10`

**Q:** How much output current can the Nano Every's 3.3 V LDO provide for my application?

**Expected:** 550 mA (max)  
**Datasheet:** ABX00028 p.[2]: "Up to 550mA output current for user application"

**Agent answered:** The Nano Every's 3.3 V LDO can provide up to 550 mA output current for a user application, with a recommended maximum of 200 mA.

## 17. `cp01`

**Q:** Which accepts a higher maximum VIN, the UNO R4 WiFi or the GIGA R1 WiFi?

**Expected:** the winner is board ABX00063  
**Datasheet:** ABX00087 p.[7]: "Input voltage from VIN pad / DC Jack"; ABX00063 p.[7]: "Input voltage from VIN pad"

**Agent answered:** The GIGA R1 WiFi accepts a higher maximum VIN: its maximum VIN is 32 V, while the UNO R4 WiFi's recommended VIN range is 6-24 V.

## 18. `cp04`

**Q:** Does the Nicla Sense ME or the Nicla Vision have the lower minimum VIN?

**Expected:** both are equal at 3.5 V  
**Datasheet:** ABX00050 p.[7]: "Input voltage from VIN pad"; ABX00051 p.[8]: "Input voltage from VIN pad"

**Agent answered:** I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions.

## 19. `cp07`

**Q:** Which uses less current in deep sleep, the Portenta C33 or the Nicla Vision?

**Expected:** the winner is board ABX00074  
**Datasheet:** ABX00074 p.[9]: "Deep Sleep Mode Current Consumption"; ABX00051 p.[8]: "Average current consumption in deep sleep mode"

**Agent answered:** The Portenta C33 has a typical deep sleep current consumption of 86 µA, while the Nicla Vision has a typical deep sleep current consumption of 374 uA. Therefore, the Portenta C33 uses less current in deep sleep.

## 20. `cp10`

**Q:** Which has more SRAM, the UNO R3 or the Nano Every?

**Expected:** the winner is board ABX00028  
**Datasheet:** A000066 p.[2]: "2 kB SRAM"; ABX00028 p.[2]: "6 kB SRAM"

**Agent answered:** The Nano Every's main ATMega4809 has 6 kB SRAM, while the UNO R3's main ATMega328P has 2 kB SRAM, so the Nano Every has more SRAM.

## 21. `tf01`

**Q:** What is the main microcontroller on the Arduino UNO R3?

**Expected:** must mention: ATmega328P  
**Datasheet:** A000066 p.[2, 4]: "ATMega328P Processor"

**Agent answered:** The main microcontroller on the Arduino UNO R3 is the ATmega328P. The board also includes an ATmega16U2 processor.

## 22. `tf04`

**Q:** Which wireless module is on the MKR WiFi 1010?

**Expected:** must mention: W102  
**Datasheet:** ABX00023 p.[1]: "the Nina W102"

**Agent answered:** The MKR WiFi 1010 uses the Nina W102 wireless module, described as a u-blox NINA-W10 module.

## 23. `tf07`

**Q:** Which LoRa module is on the MKR WAN 1310?

**Expected:** must mention: CMWX1ZZABZ  
**Datasheet:** ABX00029 p.[1, 2]: "Murata CMWX1ZZABZ LoRa"

**Agent answered:** The MKR WAN 1310 uses the Murata CMWX1ZZABZ LoRa module.

## 24. `tf10`

**Q:** Which SoC powers the Nicla Sense ME?

**Expected:** must mention: nRF52832  
**Datasheet:** ABX00050 p.[11]: "powered by a nRF52832 SoC within the ANNA-B112 module"

**Agent answered:** The Nicla Sense ME is powered by the nRF52832 SoC within the ANNA-B112 module (MD1).

## 25. `tf13`

**Q:** Which IMU is on the Nicla Vision?

**Expected:** must mention: LSM6DSOX  
**Datasheet:** ABX00051 p.[3, 12]: "LSM6DSOX 6-axis IMU"

**Agent answered:** The Nicla Vision uses the LSM6DSOX 6-axis IMU (U3).

## 26. `tf16`

**Q:** How much flash and RAM does the Nano 33 BLE Rev2's module have?

**Expected:** must mention: 1 MB, 256 kB  
**Datasheet:** ABX00071 p.[3]: "1 MB Flash + 256 kB RAM"

**Agent answered:** The Nano 33 BLE Rev2's NINA B306 module has 1 MB of Flash and 256 kB of RAM.

## 27. `pn01`

**Q:** On the UNO R3, what is the IOREF pin connected to?

**Expected:** must mention: 5V  
**Datasheet:** A000066 p.[10]: "Reference for digital logic V - connected to 5V"

**Agent answered:** On the Arduino UNO R3, the IOREF pin is the reference for digital logic V and is connected to 5V.

## 28. `pn04`

**Q:** Which MKR WiFi 1010 header pin can be used as a DAC output?

**Expected:** must mention: A0  
**Datasheet:** ABX00023 p.[10]: "A0/DAC0 Analog ADC in/DAC out"

**Agent answered:** Header pin 2, labeled A0/DAC0, can be used as a DAC output.

## 29. `pn07`

**Q:** Which Nano Every pin is the SPI clock (SCK)?

**Expected:** must mention: D13  
**Datasheet:** ABX00028 p.[8]: "D13 Digital SPI SCK, GPIO"

**Agent answered:** On the Arduino Nano Every, the SPI clock (SCK) is on pin 1, labeled D13.

## 30. `pn10`

**Q:** Where is the reset pin on the Nicla Sense ME?

**Expected:** must mention: P5  
**Datasheet:** ABX00050 p.[16]: "P5 RESET Digital Reset Pin"

**Agent answered:** On the Nicla Sense ME, the reset pin is P5 on the J2 Fins header, listed as RESET (Digital).
