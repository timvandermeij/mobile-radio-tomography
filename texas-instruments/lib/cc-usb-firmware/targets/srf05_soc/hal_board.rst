                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ANSI-C Compiler
                                      3 ; Version 3.5.0 #9253 (Dec  6 2015) (Linux)
                                      4 ; This file was generated Wed Jun  1 13:07:01 2016
                                      5 ;--------------------------------------------------------
                                      6 	.module hal_board
                                      7 	.optsdcc -mmcs51 --model-large
                                      8 	
                                      9 ;--------------------------------------------------------
                                     10 ; Public variables in this module
                                     11 ;--------------------------------------------------------
                                     12 	.globl _halLcdInit
                                     13 	.globl _halMcuInit
                                     14 	.globl _halIntOn
                                     15 	.globl _MODE
                                     16 	.globl _RE
                                     17 	.globl _SLAVE
                                     18 	.globl _FE
                                     19 	.globl _ERR
                                     20 	.globl _RX_BYTE
                                     21 	.globl _TX_BYTE
                                     22 	.globl _ACTIVE
                                     23 	.globl _B_7
                                     24 	.globl _B_6
                                     25 	.globl _B_5
                                     26 	.globl _B_4
                                     27 	.globl _B_3
                                     28 	.globl _B_2
                                     29 	.globl _B_1
                                     30 	.globl _B_0
                                     31 	.globl _WDTIF
                                     32 	.globl _P1IF
                                     33 	.globl _UTX1IF
                                     34 	.globl _UTX0IF
                                     35 	.globl _P2IF
                                     36 	.globl _ACC_7
                                     37 	.globl _ACC_6
                                     38 	.globl _ACC_5
                                     39 	.globl _ACC_4
                                     40 	.globl _ACC_3
                                     41 	.globl _ACC_2
                                     42 	.globl _ACC_1
                                     43 	.globl _ACC_0
                                     44 	.globl _OVFIM
                                     45 	.globl _T4CH1IF
                                     46 	.globl _T4CH0IF
                                     47 	.globl _T4OVFIF
                                     48 	.globl _T3CH1IF
                                     49 	.globl _T3CH0IF
                                     50 	.globl _T3OVFIF
                                     51 	.globl _CY
                                     52 	.globl _AC
                                     53 	.globl _F0
                                     54 	.globl _RS1
                                     55 	.globl _RS0
                                     56 	.globl _OV
                                     57 	.globl _F1
                                     58 	.globl _P
                                     59 	.globl _STIF
                                     60 	.globl _P0IF
                                     61 	.globl _T4IF
                                     62 	.globl _T3IF
                                     63 	.globl _T2IF
                                     64 	.globl _T1IF
                                     65 	.globl _DMAIF
                                     66 	.globl _P0IE
                                     67 	.globl _T4IE
                                     68 	.globl _T3IE
                                     69 	.globl _T2IE
                                     70 	.globl _T1IE
                                     71 	.globl _DMAIE
                                     72 	.globl _EA
                                     73 	.globl _STIE
                                     74 	.globl _ENCIE
                                     75 	.globl _URX1IE
                                     76 	.globl _URX0IE
                                     77 	.globl _ADCIE
                                     78 	.globl _RFERRIE
                                     79 	.globl _P2_7
                                     80 	.globl _P2_6
                                     81 	.globl _P2_5
                                     82 	.globl _P2_4
                                     83 	.globl _P2_3
                                     84 	.globl _P2_2
                                     85 	.globl _P2_1
                                     86 	.globl _P2_0
                                     87 	.globl _ENCIF_1
                                     88 	.globl _ENCIF_0
                                     89 	.globl _P1_7
                                     90 	.globl _P1_6
                                     91 	.globl _P1_5
                                     92 	.globl _P1_4
                                     93 	.globl _P1_3
                                     94 	.globl _P1_2
                                     95 	.globl _P1_1
                                     96 	.globl _P1_0
                                     97 	.globl _URX1IF
                                     98 	.globl _ADCIF
                                     99 	.globl _URX0IF
                                    100 	.globl _IT1
                                    101 	.globl _RFERRIF
                                    102 	.globl _IT0
                                    103 	.globl _P0_7
                                    104 	.globl _P0_6
                                    105 	.globl _P0_5
                                    106 	.globl _P0_4
                                    107 	.globl _P0_3
                                    108 	.globl _P0_2
                                    109 	.globl _P0_1
                                    110 	.globl _P0_0
                                    111 	.globl _P2DIR
                                    112 	.globl _P1DIR
                                    113 	.globl _P0DIR
                                    114 	.globl _U1GCR
                                    115 	.globl _U1UCR
                                    116 	.globl _U1BAUD
                                    117 	.globl _U1DBUF
                                    118 	.globl _U1CSR
                                    119 	.globl _P2INP
                                    120 	.globl _P1INP
                                    121 	.globl _P2SEL
                                    122 	.globl _P1SEL
                                    123 	.globl _P0SEL
                                    124 	.globl _APCFG
                                    125 	.globl _PERCFG
                                    126 	.globl _B
                                    127 	.globl _T4CC1
                                    128 	.globl _T4CCTL1
                                    129 	.globl _T4CC0
                                    130 	.globl _T4CCTL0
                                    131 	.globl _T4CTL
                                    132 	.globl _T4CNT
                                    133 	.globl _RFIRQF0
                                    134 	.globl _IRCON2
                                    135 	.globl _T1CCTL2
                                    136 	.globl _T1CCTL1
                                    137 	.globl _T1CCTL0
                                    138 	.globl _T1CTL
                                    139 	.globl _T1CNTH
                                    140 	.globl _T1CNTL
                                    141 	.globl _RFST
                                    142 	.globl _ACC
                                    143 	.globl _T1CC2H
                                    144 	.globl _T1CC2L
                                    145 	.globl _T1CC1H
                                    146 	.globl _T1CC1L
                                    147 	.globl _T1CC0H
                                    148 	.globl _T1CC0L
                                    149 	.globl _RFD
                                    150 	.globl _TIMIF
                                    151 	.globl _DMAREQ
                                    152 	.globl _DMAARM
                                    153 	.globl _DMA0CFGH
                                    154 	.globl _DMA0CFGL
                                    155 	.globl _DMA1CFGH
                                    156 	.globl _DMA1CFGL
                                    157 	.globl _DMAIRQ
                                    158 	.globl _PSW
                                    159 	.globl _T3CC1
                                    160 	.globl _T3CCTL1
                                    161 	.globl _T3CC0
                                    162 	.globl _T3CCTL0
                                    163 	.globl _T3CTL
                                    164 	.globl _T3CNT
                                    165 	.globl _WDCTL
                                    166 	.globl _MEMCTR
                                    167 	.globl _CLKCONCMD
                                    168 	.globl _U0GCR
                                    169 	.globl _U0UCR
                                    170 	.globl _T2MSEL
                                    171 	.globl _U0BAUD
                                    172 	.globl _U0DBUF
                                    173 	.globl _IRCON
                                    174 	.globl _RFERRF
                                    175 	.globl _SLEEPCMD
                                    176 	.globl _RNDH
                                    177 	.globl _RNDL
                                    178 	.globl _ADCH
                                    179 	.globl _ADCL
                                    180 	.globl _IP1
                                    181 	.globl _IEN1
                                    182 	.globl _ADCCON3
                                    183 	.globl _ADCCON2
                                    184 	.globl _ADCCON1
                                    185 	.globl _ENCCS
                                    186 	.globl _ENCDO
                                    187 	.globl _ENCDI
                                    188 	.globl _T1STAT
                                    189 	.globl _PMUX
                                    190 	.globl _STLOAD
                                    191 	.globl _P2IEN
                                    192 	.globl _P0IEN
                                    193 	.globl _IP0
                                    194 	.globl _IEN0
                                    195 	.globl _T2IRQM
                                    196 	.globl _T2MOVF2
                                    197 	.globl _T2MOVF1
                                    198 	.globl _T2MOVF0
                                    199 	.globl _T2M1
                                    200 	.globl _T2M0
                                    201 	.globl _T2IRQF
                                    202 	.globl _P2
                                    203 	.globl _FMAP
                                    204 	.globl _PSBANK
                                    205 	.globl _CLKCONSTA
                                    206 	.globl _SLEEPSTA
                                    207 	.globl _T2EVTCFG
                                    208 	.globl _S1CON
                                    209 	.globl _IEN2
                                    210 	.globl _S0CON
                                    211 	.globl _ST2
                                    212 	.globl _ST1
                                    213 	.globl _ST0
                                    214 	.globl _T2CTRL
                                    215 	.globl __XPAGE
                                    216 	.globl _MPAGE
                                    217 	.globl _DPS
                                    218 	.globl _RFIRQF1
                                    219 	.globl _P1
                                    220 	.globl _P0INP
                                    221 	.globl _P1IEN
                                    222 	.globl _PICTL
                                    223 	.globl _P2IFG
                                    224 	.globl _P1IFG
                                    225 	.globl _P0IFG
                                    226 	.globl _TCON
                                    227 	.globl _PCON
                                    228 	.globl _U0CSR
                                    229 	.globl _DPH1
                                    230 	.globl _DPL1
                                    231 	.globl _DPH0
                                    232 	.globl _DPL0
                                    233 	.globl _SP
                                    234 	.globl _P0
                                    235 	.globl _TXFILTCFG
                                    236 	.globl _RFC_OBS_CTRL2
                                    237 	.globl _RFC_OBS_CTRL1
                                    238 	.globl _RFC_OBS_CTRL0
                                    239 	.globl _CSPT
                                    240 	.globl _CSPZ
                                    241 	.globl _CSPY
                                    242 	.globl _CSPX
                                    243 	.globl _CSPSTAT
                                    244 	.globl _CSPCTRL
                                    245 	.globl _CSPPROG23
                                    246 	.globl _CSPPROG22
                                    247 	.globl _CSPPROG21
                                    248 	.globl _CSPPROG20
                                    249 	.globl _CSPPROG19
                                    250 	.globl _CSPPROG18
                                    251 	.globl _CSPPROG17
                                    252 	.globl _CSPPROG16
                                    253 	.globl _CSPPROG15
                                    254 	.globl _CSPPROG14
                                    255 	.globl _CSPPROG13
                                    256 	.globl _CSPPROG12
                                    257 	.globl _CSPPROG11
                                    258 	.globl _CSPPROG10
                                    259 	.globl _CSPPROG9
                                    260 	.globl _CSPPROG8
                                    261 	.globl _CSPPROG7
                                    262 	.globl _CSPPROG6
                                    263 	.globl _CSPPROG5
                                    264 	.globl _CSPPROG4
                                    265 	.globl _CSPPROG3
                                    266 	.globl _CSPPROG2
                                    267 	.globl _CSPPROG1
                                    268 	.globl _CSPPROG0
                                    269 	.globl _PTEST1
                                    270 	.globl _PTEST0
                                    271 	.globl _ATEST
                                    272 	.globl _DACTEST2
                                    273 	.globl _DACTEST1
                                    274 	.globl _DACTEST0
                                    275 	.globl _MDMTEST1
                                    276 	.globl _MDMTEST0
                                    277 	.globl _ADCTEST2
                                    278 	.globl _ADCTEST1
                                    279 	.globl _ADCTEST0
                                    280 	.globl _AGCCTRL3
                                    281 	.globl _AGCCTRL2
                                    282 	.globl _AGCCTRL1
                                    283 	.globl _AGCCTRL0
                                    284 	.globl _FSCAL3
                                    285 	.globl _FSCAL2
                                    286 	.globl _FSCAL1
                                    287 	.globl _FSCTRL
                                    288 	.globl _RXCTRL
                                    289 	.globl _FREQEST
                                    290 	.globl _MDMCTRL1
                                    291 	.globl _MDMCTRL0
                                    292 	.globl _RFRND
                                    293 	.globl _OPAMPMC
                                    294 	.globl _RFERRM
                                    295 	.globl _RFIRQM1
                                    296 	.globl _RFIRQM0
                                    297 	.globl _TXLAST_PTR
                                    298 	.globl _TXFIRST_PTR
                                    299 	.globl _RXP1_PTR
                                    300 	.globl _RXLAST_PTR
                                    301 	.globl _RXFIRST_PTR
                                    302 	.globl _TXFIFOCNT
                                    303 	.globl _RXFIFOCNT
                                    304 	.globl _RXFIRST
                                    305 	.globl _RSSISTAT
                                    306 	.globl _RSSI
                                    307 	.globl _CCACTRL1
                                    308 	.globl _CCACTRL0
                                    309 	.globl _FSMCTRL
                                    310 	.globl _FIFOPCTRL
                                    311 	.globl _FSMSTAT1
                                    312 	.globl _FSMSTAT0
                                    313 	.globl _TXCTRL
                                    314 	.globl _TXPOWER
                                    315 	.globl _FREQCTRL
                                    316 	.globl _FREQTUNE
                                    317 	.globl _RXMASKCLR
                                    318 	.globl _RXMASKSET
                                    319 	.globl _RXENABLE
                                    320 	.globl _FRMCTRL1
                                    321 	.globl _FRMCTRL0
                                    322 	.globl _SRCEXTEN2
                                    323 	.globl _SRCEXTEN1
                                    324 	.globl _SRCEXTEN0
                                    325 	.globl _SRCSHORTEN2
                                    326 	.globl _SRCSHORTEN1
                                    327 	.globl _SRCSHORTEN0
                                    328 	.globl _SRCMATCH
                                    329 	.globl _FRMFILT1
                                    330 	.globl _FRMFILT0
                                    331 	.globl _IEEE_ADDR
                                    332 	.globl _PANIDL
                                    333 	.globl _PANIDH
                                    334 	.globl _SHORTADDRL
                                    335 	.globl _SHORTADDRH
                                    336 	.globl _USBF5
                                    337 	.globl _USBF4
                                    338 	.globl _USBF3
                                    339 	.globl _USBF2
                                    340 	.globl _USBF1
                                    341 	.globl _USBF0
                                    342 	.globl _USBCNTH
                                    343 	.globl _USBCNTL
                                    344 	.globl _USBCNT0
                                    345 	.globl _USBCSOH
                                    346 	.globl _USBCSOL
                                    347 	.globl _USBMAXO
                                    348 	.globl _USBCSIH
                                    349 	.globl _USBCSIL
                                    350 	.globl _USBCS0
                                    351 	.globl _USBMAXI
                                    352 	.globl _USBCTRL
                                    353 	.globl _USBINDEX
                                    354 	.globl _USBFRMH
                                    355 	.globl _USBFRML
                                    356 	.globl _USBCIE
                                    357 	.globl _USBOIE
                                    358 	.globl _USBIIE
                                    359 	.globl _USBCIF
                                    360 	.globl _USBOIF
                                    361 	.globl _USBIIF
                                    362 	.globl _USBPOW
                                    363 	.globl _USBADDR
                                    364 	.globl _CMPCTL
                                    365 	.globl _OPAMPS
                                    366 	.globl _OPAMPC
                                    367 	.globl _STCV2
                                    368 	.globl _STCV1
                                    369 	.globl _STCV0
                                    370 	.globl _STCS
                                    371 	.globl _STCC
                                    372 	.globl _T1CC4H
                                    373 	.globl _T1CC4L
                                    374 	.globl _T1CC3H
                                    375 	.globl _T1CC3L
                                    376 	.globl _X_T1CC2H
                                    377 	.globl _X_T1CC2L
                                    378 	.globl _X_T1CC1H
                                    379 	.globl _X_T1CC1L
                                    380 	.globl _X_T1CC0H
                                    381 	.globl _X_T1CC0L
                                    382 	.globl _T1CCTL4
                                    383 	.globl _T1CCTL3
                                    384 	.globl _X_T1CCTL2
                                    385 	.globl _X_T1CCTL1
                                    386 	.globl _X_T1CCTL0
                                    387 	.globl _CLD
                                    388 	.globl _IRCTL
                                    389 	.globl _CHIPINFO1
                                    390 	.globl _CHIPINFO0
                                    391 	.globl _FWDATA
                                    392 	.globl _FADDRH
                                    393 	.globl _FADDRL
                                    394 	.globl _FCTL
                                    395 	.globl _IVCTRL
                                    396 	.globl _BATTMON
                                    397 	.globl _SRCRC
                                    398 	.globl _DBGDATA
                                    399 	.globl _TESTREG0
                                    400 	.globl _CHIPID
                                    401 	.globl _CHVER
                                    402 	.globl _OBSSEL5
                                    403 	.globl _OBSSEL4
                                    404 	.globl _OBSSEL3
                                    405 	.globl _OBSSEL2
                                    406 	.globl _OBSSEL1
                                    407 	.globl _OBSSEL0
                                    408 	.globl _I2CIO
                                    409 	.globl _I2CWC
                                    410 	.globl _I2CADDR
                                    411 	.globl _I2CDATA
                                    412 	.globl _I2CSTAT
                                    413 	.globl _I2CCFG
                                    414 	.globl _halBoardInit
                                    415 	.globl _halLcdSpiInit
                                    416 	.globl _halLcdSpiEna
                                    417 	.globl _halLcdSpiDis
                                    418 ;--------------------------------------------------------
                                    419 ; special function registers
                                    420 ;--------------------------------------------------------
                                    421 	.area RSEG    (ABS,DATA)
      000000                        422 	.org 0x0000
                           000080   423 _P0	=	0x0080
                           000081   424 _SP	=	0x0081
                           000082   425 _DPL0	=	0x0082
                           000083   426 _DPH0	=	0x0083
                           000084   427 _DPL1	=	0x0084
                           000085   428 _DPH1	=	0x0085
                           000086   429 _U0CSR	=	0x0086
                           000087   430 _PCON	=	0x0087
                           000088   431 _TCON	=	0x0088
                           000089   432 _P0IFG	=	0x0089
                           00008A   433 _P1IFG	=	0x008a
                           00008B   434 _P2IFG	=	0x008b
                           00008C   435 _PICTL	=	0x008c
                           00008D   436 _P1IEN	=	0x008d
                           00008F   437 _P0INP	=	0x008f
                           000090   438 _P1	=	0x0090
                           000091   439 _RFIRQF1	=	0x0091
                           000092   440 _DPS	=	0x0092
                           000093   441 _MPAGE	=	0x0093
                           000093   442 __XPAGE	=	0x0093
                           000094   443 _T2CTRL	=	0x0094
                           000095   444 _ST0	=	0x0095
                           000096   445 _ST1	=	0x0096
                           000097   446 _ST2	=	0x0097
                           000098   447 _S0CON	=	0x0098
                           00009A   448 _IEN2	=	0x009a
                           00009B   449 _S1CON	=	0x009b
                           00009C   450 _T2EVTCFG	=	0x009c
                           00009D   451 _SLEEPSTA	=	0x009d
                           00009E   452 _CLKCONSTA	=	0x009e
                           00009F   453 _PSBANK	=	0x009f
                           00009F   454 _FMAP	=	0x009f
                           0000A0   455 _P2	=	0x00a0
                           0000A1   456 _T2IRQF	=	0x00a1
                           0000A2   457 _T2M0	=	0x00a2
                           0000A3   458 _T2M1	=	0x00a3
                           0000A4   459 _T2MOVF0	=	0x00a4
                           0000A5   460 _T2MOVF1	=	0x00a5
                           0000A6   461 _T2MOVF2	=	0x00a6
                           0000A7   462 _T2IRQM	=	0x00a7
                           0000A8   463 _IEN0	=	0x00a8
                           0000A9   464 _IP0	=	0x00a9
                           0000AB   465 _P0IEN	=	0x00ab
                           0000AC   466 _P2IEN	=	0x00ac
                           0000AD   467 _STLOAD	=	0x00ad
                           0000AE   468 _PMUX	=	0x00ae
                           0000AF   469 _T1STAT	=	0x00af
                           0000B1   470 _ENCDI	=	0x00b1
                           0000B2   471 _ENCDO	=	0x00b2
                           0000B3   472 _ENCCS	=	0x00b3
                           0000B4   473 _ADCCON1	=	0x00b4
                           0000B5   474 _ADCCON2	=	0x00b5
                           0000B6   475 _ADCCON3	=	0x00b6
                           0000B8   476 _IEN1	=	0x00b8
                           0000B9   477 _IP1	=	0x00b9
                           0000BA   478 _ADCL	=	0x00ba
                           0000BB   479 _ADCH	=	0x00bb
                           0000BC   480 _RNDL	=	0x00bc
                           0000BD   481 _RNDH	=	0x00bd
                           0000BE   482 _SLEEPCMD	=	0x00be
                           0000BF   483 _RFERRF	=	0x00bf
                           0000C0   484 _IRCON	=	0x00c0
                           0000C1   485 _U0DBUF	=	0x00c1
                           0000C2   486 _U0BAUD	=	0x00c2
                           0000C3   487 _T2MSEL	=	0x00c3
                           0000C4   488 _U0UCR	=	0x00c4
                           0000C5   489 _U0GCR	=	0x00c5
                           0000C6   490 _CLKCONCMD	=	0x00c6
                           0000C7   491 _MEMCTR	=	0x00c7
                           0000C9   492 _WDCTL	=	0x00c9
                           0000CA   493 _T3CNT	=	0x00ca
                           0000CB   494 _T3CTL	=	0x00cb
                           0000CC   495 _T3CCTL0	=	0x00cc
                           0000CD   496 _T3CC0	=	0x00cd
                           0000CE   497 _T3CCTL1	=	0x00ce
                           0000CF   498 _T3CC1	=	0x00cf
                           0000D0   499 _PSW	=	0x00d0
                           0000D1   500 _DMAIRQ	=	0x00d1
                           0000D2   501 _DMA1CFGL	=	0x00d2
                           0000D3   502 _DMA1CFGH	=	0x00d3
                           0000D4   503 _DMA0CFGL	=	0x00d4
                           0000D5   504 _DMA0CFGH	=	0x00d5
                           0000D6   505 _DMAARM	=	0x00d6
                           0000D7   506 _DMAREQ	=	0x00d7
                           0000D8   507 _TIMIF	=	0x00d8
                           0000D9   508 _RFD	=	0x00d9
                           0000DA   509 _T1CC0L	=	0x00da
                           0000DB   510 _T1CC0H	=	0x00db
                           0000DC   511 _T1CC1L	=	0x00dc
                           0000DD   512 _T1CC1H	=	0x00dd
                           0000DE   513 _T1CC2L	=	0x00de
                           0000DF   514 _T1CC2H	=	0x00df
                           0000E0   515 _ACC	=	0x00e0
                           0000E1   516 _RFST	=	0x00e1
                           0000E2   517 _T1CNTL	=	0x00e2
                           0000E3   518 _T1CNTH	=	0x00e3
                           0000E4   519 _T1CTL	=	0x00e4
                           0000E5   520 _T1CCTL0	=	0x00e5
                           0000E6   521 _T1CCTL1	=	0x00e6
                           0000E7   522 _T1CCTL2	=	0x00e7
                           0000E8   523 _IRCON2	=	0x00e8
                           0000E9   524 _RFIRQF0	=	0x00e9
                           0000EA   525 _T4CNT	=	0x00ea
                           0000EB   526 _T4CTL	=	0x00eb
                           0000EC   527 _T4CCTL0	=	0x00ec
                           0000ED   528 _T4CC0	=	0x00ed
                           0000EE   529 _T4CCTL1	=	0x00ee
                           0000EF   530 _T4CC1	=	0x00ef
                           0000F0   531 _B	=	0x00f0
                           0000F1   532 _PERCFG	=	0x00f1
                           0000F2   533 _APCFG	=	0x00f2
                           0000F3   534 _P0SEL	=	0x00f3
                           0000F4   535 _P1SEL	=	0x00f4
                           0000F5   536 _P2SEL	=	0x00f5
                           0000F6   537 _P1INP	=	0x00f6
                           0000F7   538 _P2INP	=	0x00f7
                           0000F8   539 _U1CSR	=	0x00f8
                           0000F9   540 _U1DBUF	=	0x00f9
                           0000FA   541 _U1BAUD	=	0x00fa
                           0000FB   542 _U1UCR	=	0x00fb
                           0000FC   543 _U1GCR	=	0x00fc
                           0000FD   544 _P0DIR	=	0x00fd
                           0000FE   545 _P1DIR	=	0x00fe
                           0000FF   546 _P2DIR	=	0x00ff
                                    547 ;--------------------------------------------------------
                                    548 ; special function bits
                                    549 ;--------------------------------------------------------
                                    550 	.area RSEG    (ABS,DATA)
      000000                        551 	.org 0x0000
                           000080   552 _P0_0	=	0x0080
                           000081   553 _P0_1	=	0x0081
                           000082   554 _P0_2	=	0x0082
                           000083   555 _P0_3	=	0x0083
                           000084   556 _P0_4	=	0x0084
                           000085   557 _P0_5	=	0x0085
                           000086   558 _P0_6	=	0x0086
                           000087   559 _P0_7	=	0x0087
                           000088   560 _IT0	=	0x0088
                           000089   561 _RFERRIF	=	0x0089
                           00008A   562 _IT1	=	0x008a
                           00008B   563 _URX0IF	=	0x008b
                           00008D   564 _ADCIF	=	0x008d
                           00008F   565 _URX1IF	=	0x008f
                           000090   566 _P1_0	=	0x0090
                           000091   567 _P1_1	=	0x0091
                           000092   568 _P1_2	=	0x0092
                           000093   569 _P1_3	=	0x0093
                           000094   570 _P1_4	=	0x0094
                           000095   571 _P1_5	=	0x0095
                           000096   572 _P1_6	=	0x0096
                           000097   573 _P1_7	=	0x0097
                           000098   574 _ENCIF_0	=	0x0098
                           000099   575 _ENCIF_1	=	0x0099
                           0000A0   576 _P2_0	=	0x00a0
                           0000A1   577 _P2_1	=	0x00a1
                           0000A2   578 _P2_2	=	0x00a2
                           0000A3   579 _P2_3	=	0x00a3
                           0000A4   580 _P2_4	=	0x00a4
                           0000A5   581 _P2_5	=	0x00a5
                           0000A6   582 _P2_6	=	0x00a6
                           0000A7   583 _P2_7	=	0x00a7
                           0000A8   584 _RFERRIE	=	0x00a8
                           0000A9   585 _ADCIE	=	0x00a9
                           0000AA   586 _URX0IE	=	0x00aa
                           0000AB   587 _URX1IE	=	0x00ab
                           0000AC   588 _ENCIE	=	0x00ac
                           0000AD   589 _STIE	=	0x00ad
                           0000AF   590 _EA	=	0x00af
                           0000B8   591 _DMAIE	=	0x00b8
                           0000B9   592 _T1IE	=	0x00b9
                           0000BA   593 _T2IE	=	0x00ba
                           0000BB   594 _T3IE	=	0x00bb
                           0000BC   595 _T4IE	=	0x00bc
                           0000BD   596 _P0IE	=	0x00bd
                           0000C0   597 _DMAIF	=	0x00c0
                           0000C1   598 _T1IF	=	0x00c1
                           0000C2   599 _T2IF	=	0x00c2
                           0000C3   600 _T3IF	=	0x00c3
                           0000C4   601 _T4IF	=	0x00c4
                           0000C5   602 _P0IF	=	0x00c5
                           0000C7   603 _STIF	=	0x00c7
                           0000D0   604 _P	=	0x00d0
                           0000D1   605 _F1	=	0x00d1
                           0000D2   606 _OV	=	0x00d2
                           0000D3   607 _RS0	=	0x00d3
                           0000D4   608 _RS1	=	0x00d4
                           0000D5   609 _F0	=	0x00d5
                           0000D6   610 _AC	=	0x00d6
                           0000D7   611 _CY	=	0x00d7
                           0000D8   612 _T3OVFIF	=	0x00d8
                           0000D9   613 _T3CH0IF	=	0x00d9
                           0000DA   614 _T3CH1IF	=	0x00da
                           0000DB   615 _T4OVFIF	=	0x00db
                           0000DC   616 _T4CH0IF	=	0x00dc
                           0000DD   617 _T4CH1IF	=	0x00dd
                           0000DE   618 _OVFIM	=	0x00de
                           0000E0   619 _ACC_0	=	0x00e0
                           0000E1   620 _ACC_1	=	0x00e1
                           0000E2   621 _ACC_2	=	0x00e2
                           0000E3   622 _ACC_3	=	0x00e3
                           0000E4   623 _ACC_4	=	0x00e4
                           0000E5   624 _ACC_5	=	0x00e5
                           0000E6   625 _ACC_6	=	0x00e6
                           0000E7   626 _ACC_7	=	0x00e7
                           0000E8   627 _P2IF	=	0x00e8
                           0000E9   628 _UTX0IF	=	0x00e9
                           0000EA   629 _UTX1IF	=	0x00ea
                           0000EB   630 _P1IF	=	0x00eb
                           0000EC   631 _WDTIF	=	0x00ec
                           0000F0   632 _B_0	=	0x00f0
                           0000F1   633 _B_1	=	0x00f1
                           0000F2   634 _B_2	=	0x00f2
                           0000F3   635 _B_3	=	0x00f3
                           0000F4   636 _B_4	=	0x00f4
                           0000F5   637 _B_5	=	0x00f5
                           0000F6   638 _B_6	=	0x00f6
                           0000F7   639 _B_7	=	0x00f7
                           0000F8   640 _ACTIVE	=	0x00f8
                           0000F9   641 _TX_BYTE	=	0x00f9
                           0000FA   642 _RX_BYTE	=	0x00fa
                           0000FB   643 _ERR	=	0x00fb
                           0000FC   644 _FE	=	0x00fc
                           0000FD   645 _SLAVE	=	0x00fd
                           0000FE   646 _RE	=	0x00fe
                           0000FF   647 _MODE	=	0x00ff
                                    648 ;--------------------------------------------------------
                                    649 ; overlayable register banks
                                    650 ;--------------------------------------------------------
                                    651 	.area REG_BANK_0	(REL,OVR,DATA)
      000000                        652 	.ds 8
                                    653 ;--------------------------------------------------------
                                    654 ; internal ram data
                                    655 ;--------------------------------------------------------
                                    656 	.area DSEG    (DATA)
                                    657 ;--------------------------------------------------------
                                    658 ; overlayable items in internal ram 
                                    659 ;--------------------------------------------------------
                                    660 	.area	OSEG    (OVR,DATA)
                                    661 ;--------------------------------------------------------
                                    662 ; indirectly addressable internal ram data
                                    663 ;--------------------------------------------------------
                                    664 	.area ISEG    (DATA)
                                    665 ;--------------------------------------------------------
                                    666 ; absolute internal ram data
                                    667 ;--------------------------------------------------------
                                    668 	.area IABS    (ABS,DATA)
                                    669 	.area IABS    (ABS,DATA)
                                    670 ;--------------------------------------------------------
                                    671 ; bit data
                                    672 ;--------------------------------------------------------
                                    673 	.area BSEG    (BIT)
                                    674 ;--------------------------------------------------------
                                    675 ; paged external ram data
                                    676 ;--------------------------------------------------------
                                    677 	.area PSEG    (PAG,XDATA)
                                    678 ;--------------------------------------------------------
                                    679 ; external ram data
                                    680 ;--------------------------------------------------------
                                    681 	.area XSEG    (XDATA)
                           006230   682 _I2CCFG	=	0x6230
                           006231   683 _I2CSTAT	=	0x6231
                           006232   684 _I2CDATA	=	0x6232
                           006233   685 _I2CADDR	=	0x6233
                           006234   686 _I2CWC	=	0x6234
                           006235   687 _I2CIO	=	0x6235
                           006243   688 _OBSSEL0	=	0x6243
                           006244   689 _OBSSEL1	=	0x6244
                           006245   690 _OBSSEL2	=	0x6245
                           006246   691 _OBSSEL3	=	0x6246
                           006247   692 _OBSSEL4	=	0x6247
                           006248   693 _OBSSEL5	=	0x6248
                           006249   694 _CHVER	=	0x6249
                           00624A   695 _CHIPID	=	0x624a
                           00624B   696 _TESTREG0	=	0x624b
                           006260   697 _DBGDATA	=	0x6260
                           006262   698 _SRCRC	=	0x6262
                           006264   699 _BATTMON	=	0x6264
                           006265   700 _IVCTRL	=	0x6265
                           006270   701 _FCTL	=	0x6270
                           006271   702 _FADDRL	=	0x6271
                           006272   703 _FADDRH	=	0x6272
                           006273   704 _FWDATA	=	0x6273
                           006276   705 _CHIPINFO0	=	0x6276
                           006277   706 _CHIPINFO1	=	0x6277
                           006281   707 _IRCTL	=	0x6281
                           006290   708 _CLD	=	0x6290
                           0062A0   709 _X_T1CCTL0	=	0x62a0
                           0062A1   710 _X_T1CCTL1	=	0x62a1
                           0062A2   711 _X_T1CCTL2	=	0x62a2
                           0062A3   712 _T1CCTL3	=	0x62a3
                           0062A4   713 _T1CCTL4	=	0x62a4
                           0062A6   714 _X_T1CC0L	=	0x62a6
                           0062A7   715 _X_T1CC0H	=	0x62a7
                           0062A8   716 _X_T1CC1L	=	0x62a8
                           0062A9   717 _X_T1CC1H	=	0x62a9
                           0062AA   718 _X_T1CC2L	=	0x62aa
                           0062AB   719 _X_T1CC2H	=	0x62ab
                           0062AC   720 _T1CC3L	=	0x62ac
                           0062AD   721 _T1CC3H	=	0x62ad
                           0062AE   722 _T1CC4L	=	0x62ae
                           0062AF   723 _T1CC4H	=	0x62af
                           0062B0   724 _STCC	=	0x62b0
                           0062B1   725 _STCS	=	0x62b1
                           0062B2   726 _STCV0	=	0x62b2
                           0062B3   727 _STCV1	=	0x62b3
                           0062B4   728 _STCV2	=	0x62b4
                           0062C0   729 _OPAMPC	=	0x62c0
                           0062C1   730 _OPAMPS	=	0x62c1
                           0062D0   731 _CMPCTL	=	0x62d0
                           006200   732 _USBADDR	=	0x6200
                           006201   733 _USBPOW	=	0x6201
                           006202   734 _USBIIF	=	0x6202
                           006204   735 _USBOIF	=	0x6204
                           006206   736 _USBCIF	=	0x6206
                           006207   737 _USBIIE	=	0x6207
                           006209   738 _USBOIE	=	0x6209
                           00620B   739 _USBCIE	=	0x620b
                           00620C   740 _USBFRML	=	0x620c
                           00620D   741 _USBFRMH	=	0x620d
                           00620E   742 _USBINDEX	=	0x620e
                           00620F   743 _USBCTRL	=	0x620f
                           006210   744 _USBMAXI	=	0x6210
                           006211   745 _USBCS0	=	0x6211
                           006211   746 _USBCSIL	=	0x6211
                           006212   747 _USBCSIH	=	0x6212
                           006213   748 _USBMAXO	=	0x6213
                           006214   749 _USBCSOL	=	0x6214
                           006215   750 _USBCSOH	=	0x6215
                           006216   751 _USBCNT0	=	0x6216
                           006216   752 _USBCNTL	=	0x6216
                           006217   753 _USBCNTH	=	0x6217
                           006220   754 _USBF0	=	0x6220
                           006222   755 _USBF1	=	0x6222
                           006224   756 _USBF2	=	0x6224
                           006226   757 _USBF3	=	0x6226
                           006228   758 _USBF4	=	0x6228
                           00622A   759 _USBF5	=	0x622a
                           006174   760 _SHORTADDRH	=	0x6174
                           006175   761 _SHORTADDRL	=	0x6175
                           006172   762 _PANIDH	=	0x6172
                           006173   763 _PANIDL	=	0x6173
                           00616A   764 _IEEE_ADDR	=	0x616a
                           006180   765 _FRMFILT0	=	0x6180
                           006181   766 _FRMFILT1	=	0x6181
                           006182   767 _SRCMATCH	=	0x6182
                           006183   768 _SRCSHORTEN0	=	0x6183
                           006184   769 _SRCSHORTEN1	=	0x6184
                           006185   770 _SRCSHORTEN2	=	0x6185
                           006186   771 _SRCEXTEN0	=	0x6186
                           006187   772 _SRCEXTEN1	=	0x6187
                           006188   773 _SRCEXTEN2	=	0x6188
                           006189   774 _FRMCTRL0	=	0x6189
                           00618A   775 _FRMCTRL1	=	0x618a
                           00618B   776 _RXENABLE	=	0x618b
                           00618C   777 _RXMASKSET	=	0x618c
                           00618D   778 _RXMASKCLR	=	0x618d
                           00618E   779 _FREQTUNE	=	0x618e
                           00618F   780 _FREQCTRL	=	0x618f
                           006190   781 _TXPOWER	=	0x6190
                           006191   782 _TXCTRL	=	0x6191
                           006192   783 _FSMSTAT0	=	0x6192
                           006193   784 _FSMSTAT1	=	0x6193
                           006194   785 _FIFOPCTRL	=	0x6194
                           006195   786 _FSMCTRL	=	0x6195
                           006196   787 _CCACTRL0	=	0x6196
                           006197   788 _CCACTRL1	=	0x6197
                           006198   789 _RSSI	=	0x6198
                           006199   790 _RSSISTAT	=	0x6199
                           00619A   791 _RXFIRST	=	0x619a
                           00619B   792 _RXFIFOCNT	=	0x619b
                           00619C   793 _TXFIFOCNT	=	0x619c
                           00619D   794 _RXFIRST_PTR	=	0x619d
                           00619E   795 _RXLAST_PTR	=	0x619e
                           00619F   796 _RXP1_PTR	=	0x619f
                           0061A1   797 _TXFIRST_PTR	=	0x61a1
                           0061A2   798 _TXLAST_PTR	=	0x61a2
                           0061A3   799 _RFIRQM0	=	0x61a3
                           0061A4   800 _RFIRQM1	=	0x61a4
                           0061A5   801 _RFERRM	=	0x61a5
                           0061A6   802 _OPAMPMC	=	0x61a6
                           0061A7   803 _RFRND	=	0x61a7
                           0061A8   804 _MDMCTRL0	=	0x61a8
                           0061A9   805 _MDMCTRL1	=	0x61a9
                           0061AA   806 _FREQEST	=	0x61aa
                           0061AB   807 _RXCTRL	=	0x61ab
                           0061AC   808 _FSCTRL	=	0x61ac
                           0061AE   809 _FSCAL1	=	0x61ae
                           0061AF   810 _FSCAL2	=	0x61af
                           0061B0   811 _FSCAL3	=	0x61b0
                           0061B1   812 _AGCCTRL0	=	0x61b1
                           0061B2   813 _AGCCTRL1	=	0x61b2
                           0061B3   814 _AGCCTRL2	=	0x61b3
                           0061B4   815 _AGCCTRL3	=	0x61b4
                           0061B5   816 _ADCTEST0	=	0x61b5
                           0061B6   817 _ADCTEST1	=	0x61b6
                           0061B7   818 _ADCTEST2	=	0x61b7
                           0061B8   819 _MDMTEST0	=	0x61b8
                           0061B9   820 _MDMTEST1	=	0x61b9
                           0061BA   821 _DACTEST0	=	0x61ba
                           0061BB   822 _DACTEST1	=	0x61bb
                           0061BC   823 _DACTEST2	=	0x61bc
                           0061BD   824 _ATEST	=	0x61bd
                           0061BE   825 _PTEST0	=	0x61be
                           0061BF   826 _PTEST1	=	0x61bf
                           0061C0   827 _CSPPROG0	=	0x61c0
                           0061C1   828 _CSPPROG1	=	0x61c1
                           0061C2   829 _CSPPROG2	=	0x61c2
                           0061C3   830 _CSPPROG3	=	0x61c3
                           0061C4   831 _CSPPROG4	=	0x61c4
                           0061C5   832 _CSPPROG5	=	0x61c5
                           0061C6   833 _CSPPROG6	=	0x61c6
                           0061C7   834 _CSPPROG7	=	0x61c7
                           0061C8   835 _CSPPROG8	=	0x61c8
                           0061C9   836 _CSPPROG9	=	0x61c9
                           0061CA   837 _CSPPROG10	=	0x61ca
                           0061CB   838 _CSPPROG11	=	0x61cb
                           0061CC   839 _CSPPROG12	=	0x61cc
                           0061CD   840 _CSPPROG13	=	0x61cd
                           0061CE   841 _CSPPROG14	=	0x61ce
                           0061CF   842 _CSPPROG15	=	0x61cf
                           0061D0   843 _CSPPROG16	=	0x61d0
                           0061D1   844 _CSPPROG17	=	0x61d1
                           0061D2   845 _CSPPROG18	=	0x61d2
                           0061D3   846 _CSPPROG19	=	0x61d3
                           0061D4   847 _CSPPROG20	=	0x61d4
                           0061D5   848 _CSPPROG21	=	0x61d5
                           0061D6   849 _CSPPROG22	=	0x61d6
                           0061D7   850 _CSPPROG23	=	0x61d7
                           0061E0   851 _CSPCTRL	=	0x61e0
                           0061E1   852 _CSPSTAT	=	0x61e1
                           0061E2   853 _CSPX	=	0x61e2
                           0061E3   854 _CSPY	=	0x61e3
                           0061E4   855 _CSPZ	=	0x61e4
                           0061E5   856 _CSPT	=	0x61e5
                           0061EB   857 _RFC_OBS_CTRL0	=	0x61eb
                           0061EC   858 _RFC_OBS_CTRL1	=	0x61ec
                           0061ED   859 _RFC_OBS_CTRL2	=	0x61ed
                           0061FA   860 _TXFILTCFG	=	0x61fa
                                    861 ;--------------------------------------------------------
                                    862 ; absolute external ram data
                                    863 ;--------------------------------------------------------
                                    864 	.area XABS    (ABS,XDATA)
                                    865 ;--------------------------------------------------------
                                    866 ; external initialized ram data
                                    867 ;--------------------------------------------------------
                                    868 	.area XISEG   (XDATA)
                                    869 	.area HOME    (CODE)
                                    870 	.area GSINIT0 (CODE)
                                    871 	.area GSINIT1 (CODE)
                                    872 	.area GSINIT2 (CODE)
                                    873 	.area GSINIT3 (CODE)
                                    874 	.area GSINIT4 (CODE)
                                    875 	.area GSINIT5 (CODE)
                                    876 	.area GSINIT  (CODE)
                                    877 	.area GSFINAL (CODE)
                                    878 	.area CSEG    (CODE)
                                    879 ;--------------------------------------------------------
                                    880 ; global & static initialisations
                                    881 ;--------------------------------------------------------
                                    882 	.area HOME    (CODE)
                                    883 	.area GSINIT  (CODE)
                                    884 	.area GSFINAL (CODE)
                                    885 	.area GSINIT  (CODE)
                                    886 ;--------------------------------------------------------
                                    887 ; Home
                                    888 ;--------------------------------------------------------
                                    889 	.area HOME    (CODE)
                                    890 	.area HOME    (CODE)
                                    891 ;--------------------------------------------------------
                                    892 ; code
                                    893 ;--------------------------------------------------------
                                    894 	.area CSEG    (CODE)
                                    895 ;------------------------------------------------------------
                                    896 ;Allocation info for local variables in function 'halBoardInit'
                                    897 ;------------------------------------------------------------
                                    898 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:52: void halBoardInit(void)
                                    899 ;	-----------------------------------------
                                    900 ;	 function halBoardInit
                                    901 ;	-----------------------------------------
      0003A6                        902 _halBoardInit:
                           000007   903 	ar7 = 0x07
                           000006   904 	ar6 = 0x06
                           000005   905 	ar5 = 0x05
                           000004   906 	ar4 = 0x04
                           000003   907 	ar3 = 0x03
                           000002   908 	ar2 = 0x02
                           000001   909 	ar1 = 0x01
                           000000   910 	ar0 = 0x00
                                    911 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:54: halMcuInit();
      0003A6 12 02 B5         [24]  912 	lcall	_halMcuInit
                                    913 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:62: MCU_IO_DIR_OUTPUT(HAL_BOARD_IO_LED_1_PORT, HAL_BOARD_IO_LED_1_PIN);
      0003A9 43 FE 01         [24]  914 	orl	_P1DIR,#0x01
                                    915 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:63: HAL_LED_CLR_1();
      0003AC C2 90            [12]  916 	clr	_P1_0
                                    917 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:64: MCU_IO_DIR_OUTPUT(HAL_BOARD_IO_LED_2_PORT, HAL_BOARD_IO_LED_2_PIN);
      0003AE 43 FE 02         [24]  918 	orl	_P1DIR,#0x02
                                    919 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:65: HAL_LED_CLR_2();
      0003B1 C2 91            [12]  920 	clr	_P1_1
                                    921 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:66: MCU_IO_DIR_OUTPUT(HAL_BOARD_IO_LED_3_PORT, HAL_BOARD_IO_LED_3_PIN);
      0003B3 43 FE 10         [24]  922 	orl	_P1DIR,#0x10
                                    923 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:67: HAL_LED_CLR_3();
      0003B6 C2 94            [12]  924 	clr	_P1_4
                                    925 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:68: MCU_IO_DIR_OUTPUT(HAL_BOARD_IO_LED_4_PORT, HAL_BOARD_IO_LED_4_PIN);
      0003B8 43 FD 02         [24]  926 	orl	_P0DIR,#0x02
                                    927 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:69: HAL_LED_CLR_4();
      0003BB C2 81            [12]  928 	clr	_P0_1
                                    929 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:73: MCU_IO_INPUT(HAL_BOARD_IO_BTN_1_PORT, HAL_BOARD_IO_BTN_1_PIN, MCU_IO_TRISTATE);
      0003BD AF F3            [24]  930 	mov	r7,_P0SEL
      0003BF 74 FD            [12]  931 	mov	a,#0xFD
      0003C1 5F               [12]  932 	anl	a,r7
      0003C2 F5 F3            [12]  933 	mov	_P0SEL,a
      0003C4 AF FD            [24]  934 	mov	r7,_P0DIR
      0003C6 74 FD            [12]  935 	mov	a,#0xFD
      0003C8 5F               [12]  936 	anl	a,r7
      0003C9 F5 FD            [12]  937 	mov	_P0DIR,a
      0003CB 43 8F 02         [24]  938 	orl	_P0INP,#0x02
                                    939 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:76: MCU_IO_INPUT(HAL_BOARD_IO_JOY_MOVE_PORT, HAL_BOARD_IO_JOY_MOVE_PIN, \
      0003CE AF F5            [24]  940 	mov	r7,_P2SEL
      0003D0 74 FE            [12]  941 	mov	a,#0xFE
      0003D2 5F               [12]  942 	anl	a,r7
      0003D3 F5 F5            [12]  943 	mov	_P2SEL,a
      0003D5 AF FF            [24]  944 	mov	r7,_P2DIR
      0003D7 74 FE            [12]  945 	mov	a,#0xFE
      0003D9 5F               [12]  946 	anl	a,r7
      0003DA F5 FF            [12]  947 	mov	_P2DIR,a
      0003DC 43 F7 01         [24]  948 	orl	_P2INP,#0x01
                                    949 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:80: MCU_IO_PERIPHERAL(HAL_BOARD_IO_JOYSTICK_ADC_PORT, HAL_BOARD_IO_JOYSTICK_ADC_PIN);
      0003DF 43 F3 40         [24]  950 	orl	_P0SEL,#0x40
                                    951 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:83: halLcdSpiInit();
      0003E2 12 03 EB         [24]  952 	lcall	_halLcdSpiInit
                                    953 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:84: halLcdInit();
      0003E5 12 00 00         [24]  954 	lcall	_halLcdInit
                                    955 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:86: halIntOn();
      0003E8 02 02 04         [24]  956 	ljmp	_halIntOn
                                    957 ;------------------------------------------------------------
                                    958 ;Allocation info for local variables in function 'halLcdSpiInit'
                                    959 ;------------------------------------------------------------
                                    960 ;baud_exponent             Allocated to registers r7 
                                    961 ;baud_mantissa             Allocated to registers 
                                    962 ;------------------------------------------------------------
                                    963 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:99: void halLcdSpiInit(void)
                                    964 ;	-----------------------------------------
                                    965 ;	 function halLcdSpiInit
                                    966 ;	-----------------------------------------
      0003EB                        967 _halLcdSpiInit:
                                    968 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:106: PERCFG |= 0x02;
      0003EB 43 F1 02         [24]  969 	orl	_PERCFG,#0x02
                                    970 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:109: MCU_IO_PERIPHERAL(HAL_BOARD_IO_SPI_MISO_PORT, HAL_BOARD_IO_SPI_MISO_PIN);
      0003EE 43 F4 80         [24]  971 	orl	_P1SEL,#0x80
                                    972 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:110: MCU_IO_PERIPHERAL(HAL_BOARD_IO_SPI_MOSI_PORT, HAL_BOARD_IO_SPI_MOSI_PIN);
      0003F1 43 F4 40         [24]  973 	orl	_P1SEL,#0x40
                                    974 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:111: MCU_IO_PERIPHERAL(HAL_BOARD_IO_SPI_CLK_PORT,  HAL_BOARD_IO_SPI_CLK_PIN);
      0003F4 43 F4 20         [24]  975 	orl	_P1SEL,#0x20
                                    976 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:117: baud_exponent = 15 + CC2530_GET_CLKSPD();
      0003F7 74 01            [12]  977 	mov	a,#0x01
      0003F9 55 9E            [12]  978 	anl	a,_CLKCONSTA
      0003FB 24 0F            [12]  979 	add	a,#0x0F
      0003FD FF               [12]  980 	mov	r7,a
                                    981 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:124: U1UCR  = 0x80;      // Flush and goto IDLE state. 8-N-1.
      0003FE 75 FB 80         [24]  982 	mov	_U1UCR,#0x80
                                    983 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:125: U1CSR  = 0x00;      // SPI mode, master.
      000401 75 F8 00         [24]  984 	mov	_U1CSR,#0x00
                                    985 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:126: U1GCR  = SPI_TRANSFER_MSB_FIRST | SPI_CLOCK_PHA_0 | SPI_CLOCK_POL_LO | baud_exponent;
      000404 74 20            [12]  986 	mov	a,#0x20
      000406 4F               [12]  987 	orl	a,r7
      000407 F5 FC            [12]  988 	mov	_U1GCR,a
                                    989 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:127: U1BAUD = baud_mantissa;
      000409 75 FA 53         [24]  990 	mov	_U1BAUD,#0x53
      00040C 22               [24]  991 	ret
                                    992 ;------------------------------------------------------------
                                    993 ;Allocation info for local variables in function 'halLcdSpiEna'
                                    994 ;------------------------------------------------------------
                                    995 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:139: void halLcdSpiEna(void)
                                    996 ;	-----------------------------------------
                                    997 ;	 function halLcdSpiEna
                                    998 ;	-----------------------------------------
      00040D                        999 _halLcdSpiEna:
                                   1000 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:142: MCU_IO_PERIPHERAL(HAL_BOARD_IO_SPI_MISO_PORT, HAL_BOARD_IO_SPI_MISO_PIN);
      00040D 43 F4 80         [24] 1001 	orl	_P1SEL,#0x80
                                   1002 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:143: MCU_IO_PERIPHERAL(HAL_BOARD_IO_SPI_MOSI_PORT, HAL_BOARD_IO_SPI_MOSI_PIN);
      000410 43 F4 40         [24] 1003 	orl	_P1SEL,#0x40
                                   1004 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:144: MCU_IO_PERIPHERAL(HAL_BOARD_IO_SPI_CLK_PORT,  HAL_BOARD_IO_SPI_CLK_PIN);
      000413 43 F4 20         [24] 1005 	orl	_P1SEL,#0x20
      000416 22               [24] 1006 	ret
                                   1007 ;------------------------------------------------------------
                                   1008 ;Allocation info for local variables in function 'halLcdSpiDis'
                                   1009 ;------------------------------------------------------------
                                   1010 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:156: void halLcdSpiDis(void)
                                   1011 ;	-----------------------------------------
                                   1012 ;	 function halLcdSpiDis
                                   1013 ;	-----------------------------------------
      000417                       1014 _halLcdSpiDis:
                                   1015 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:158: MCU_IO_INPUT(HAL_BOARD_IO_SPI_MISO_PORT, HAL_BOARD_IO_SPI_MISO_PIN, MCU_IO_TRISTATE);
      000417 AF F4            [24] 1016 	mov	r7,_P1SEL
      000419 74 7F            [12] 1017 	mov	a,#0x7F
      00041B 5F               [12] 1018 	anl	a,r7
      00041C F5 F4            [12] 1019 	mov	_P1SEL,a
      00041E AF FE            [24] 1020 	mov	r7,_P1DIR
      000420 74 7F            [12] 1021 	mov	a,#0x7F
      000422 5F               [12] 1022 	anl	a,r7
      000423 F5 FE            [12] 1023 	mov	_P1DIR,a
      000425 43 F6 80         [24] 1024 	orl	_P1INP,#0x80
                                   1025 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:159: MCU_IO_INPUT(HAL_BOARD_IO_SPI_MOSI_PORT, HAL_BOARD_IO_SPI_MOSI_PIN, MCU_IO_TRISTATE);
      000428 AF F4            [24] 1026 	mov	r7,_P1SEL
      00042A 74 BF            [12] 1027 	mov	a,#0xBF
      00042C 5F               [12] 1028 	anl	a,r7
      00042D F5 F4            [12] 1029 	mov	_P1SEL,a
      00042F AF FE            [24] 1030 	mov	r7,_P1DIR
      000431 74 BF            [12] 1031 	mov	a,#0xBF
      000433 5F               [12] 1032 	anl	a,r7
      000434 F5 FE            [12] 1033 	mov	_P1DIR,a
      000436 43 F6 40         [24] 1034 	orl	_P1INP,#0x40
                                   1035 ;	/home/timvandermeij/Documenten/Universiteit/5/Masterclass/Code/playground/texas-instruments/src/cc2530/../../lib/cc-usb-firmware/targets/srf05_soc/hal_board.c:160: MCU_IO_INPUT(HAL_BOARD_IO_SPI_CLK_PORT, HAL_BOARD_IO_SPI_CLK_PIN, MCU_IO_TRISTATE);
      000439 AF F4            [24] 1036 	mov	r7,_P1SEL
      00043B 74 DF            [12] 1037 	mov	a,#0xDF
      00043D 5F               [12] 1038 	anl	a,r7
      00043E F5 F4            [12] 1039 	mov	_P1SEL,a
      000440 AF FE            [24] 1040 	mov	r7,_P1DIR
      000442 74 DF            [12] 1041 	mov	a,#0xDF
      000444 5F               [12] 1042 	anl	a,r7
      000445 F5 FE            [12] 1043 	mov	_P1DIR,a
      000447 43 F6 20         [24] 1044 	orl	_P1INP,#0x20
      00044A 22               [24] 1045 	ret
                                   1046 	.area CSEG    (CODE)
                                   1047 	.area CONST   (CODE)
                                   1048 	.area XINIT   (CODE)
                                   1049 	.area CABS    (ABS,CODE)
