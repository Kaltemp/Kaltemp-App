import {
  ChannelSale,
  SkuNode,
  StockItem,
  PendingDispatchItem,
  CreditNoteItem,
  FulfillmentProgram,
  EnviameShipment,
  LeadItem,
  AbandonedCart,
  D2CCategoryPerf,
  CampaignItem,
  DistributorItem,
  DailyTempSale
} from '../types';

export const CHANNELS_DATA: ChannelSale[] = [
  { canal: 'OFICINA', bsale: 142500000, full: 0, totalBruto: 142500000, contribucion: 48450000, neto: 119747899, txs: 142, tkp: 1003521, wow: 135000000, yoy: 121000000, twoYoy: 105000000, wowPct: 5.6, yoyPct: 17.8, twoYoyPct: 35.7, margenFrontal: 40.5, share: 22.8 },
  { canal: 'SHOWROOM', bsale: 118200000, full: 0, totalBruto: 118200000, contribucion: 42552000, neto: 99327731, txs: 185, tkp: 638918, wow: 110000000, yoy: 102000000, twoYoy: 89000000, wowPct: 7.5, yoyPct: 15.9, twoYoyPct: 32.8, margenFrontal: 42.8, share: 18.9 },
  { canal: 'D2C (SHOPIFY)', bsale: 98400000, full: 12500000, totalBruto: 110900000, contribucion: 38815000, neto: 93193277, txs: 310, tkp: 357741, wow: 95000000, yoy: 82000000, twoYoy: 64000000, wowPct: 16.7, yoyPct: 35.2, twoYoyPct: 73.3, margenFrontal: 41.7, share: 17.7 },
  { canal: 'DISTRIBUIDORES', bsale: 89600000, full: 0, totalBruto: 89600000, contribucion: 28672000, neto: 75294118, txs: 48, tkp: 1866667, wow: 82000000, yoy: 78000000, twoYoy: 70000000, wowPct: 9.3, yoyPct: 14.9, twoYoyPct: 28.0, margenFrontal: 38.1, share: 14.3 },
  { canal: 'FALABELLA', bsale: 18200000, full: 24800000, totalBruto: 43000000, contribucion: 13760000, neto: 36134454, txs: 122, tkp: 352459, wow: 39000000, yoy: 35000000, twoYoy: 28000000, wowPct: 10.3, yoyPct: 22.9, twoYoyPct: 53.6, margenFrontal: 38.1, share: 6.9 },
  { canal: 'MERCADOLIBRE', bsale: 14100000, full: 22400000, totalBruto: 36500000, contribucion: 11315000, neto: 30672269, txs: 145, tkp: 251724, wow: 32000000, yoy: 29000000, twoYoy: 21000000, wowPct: 14.1, yoyPct: 25.9, twoYoyPct: 73.8, margenFrontal: 36.9, share: 5.8 },
  { canal: 'INMOBILIARIAS', bsale: 34200000, full: 0, totalBruto: 34200000, contribucion: 11970000, neto: 28739496, txs: 12, tkp: 2850000, wow: 31000000, yoy: 26000000, twoYoy: 22000000, wowPct: 10.3, yoyPct: 31.5, twoYoyPct: 55.5, margenFrontal: 41.7, share: 5.5 },
  { canal: 'PARIS', bsale: 8400000, full: 11200000, totalBruto: 19600000, contribucion: 6076000, neto: 16470588, txs: 58, tkp: 337931, wow: 18000000, yoy: 15000000, twoYoy: 11000000, wowPct: 8.9, yoyPct: 30.7, twoYoyPct: 78.2, margenFrontal: 36.9, share: 3.1 },
  { canal: 'RIPLEY', bsale: 6200000, full: 9800000, totalBruto: 16000000, contribucion: 4800000, neto: 13445378, txs: 46, tkp: 347826, wow: 14500000, yoy: 12000000, twoYoy: 9000000, wowPct: 10.3, yoyPct: 33.3, twoYoyPct: 77.8, margenFrontal: 35.7, share: 2.6 },
  { canal: 'SERVICIO TÉCNICO', bsale: 12800000, full: 0, totalBruto: 12800000, contribucion: 5632000, neto: 10756303, txs: 88, tkp: 145455, wow: 12000000, yoy: 10500000, twoYoy: 8500000, wowPct: 6.7, yoyPct: 21.9, twoYoyPct: 50.6, margenFrontal: 52.4, share: 2.0 },
  { canal: 'WALMART MKP', bsale: 4100000, full: 2800000, totalBruto: 6900000, contribucion: 2070000, neto: 5798319, txs: 24, tkp: 287500, wow: 6000000, yoy: 4500000, twoYoy: 2000000, wowPct: 15.0, yoyPct: 53.3, twoYoyPct: 245.0, margenFrontal: 35.7, share: 1.1 },
  { canal: 'OTROS', bsale: 4600000, full: 0, totalBruto: 4600000, contribucion: 1610000, neto: 3865546, txs: 18, tkp: 255556, wow: 4200000, yoy: 3800000, twoYoy: 3000000, wowPct: 9.5, yoyPct: 21.1, twoYoyPct: 53.3, margenFrontal: 41.7, share: 0.7 },
];

export const SKU_SALES_TREE: SkuNode[] = [
  {
    id: 'p1',
    sku: 'KLES0087',
    nombre: 'ESTUFA INFRARROJA EIGER 1500W WIFI',
    categoria: '🔥 Calefacción',
    cantCy: 142, cantWow: 128, cantYoy: 110,
    ventaCy: 49558000, ventaWow: 44672000, ventaYoy: 38390000,
    netoCy: 41645378, netoYoy: 32260504, contriCy: 17907513, contriYoy: 13549412,
    pPromCy: 349000, pPromWow: 349000, pPromYoy: 349000, margenCy: 43.0, margenYoy: 42.0,
    vendedores: [
      {
        id: 'p1_v1', nombre: 'WILLIAM GARRIDO',
        cantCy: 68, cantWow: 60, cantYoy: 50,
        ventaCy: 23732000, ventaWow: 20940000, ventaYoy: 17450000,
        netoCy: 19942857, contriCy: 8575428, pPromCy: 349000, margenCy: 43.0,
        documentos: [
          {
            id: 'p1_v1_d1', nombre: 'Factura Electrónica N° 18420',
            cantCy: 40, ventaCy: 13960000, ventaWow: 12215000, ventaYoy: 10470000,
            netoCy: 11731092, contriCy: 5044370, pPromCy: 349000, margenCy: 43.0,
            clientes: [
              { id: 'c1', nombre: 'CONSTRUCTORA VALLE CENTRAL S.A.', cantCy: 25, ventaCy: 8725000, netoCy: 7331932, contriCy: 3152731, pPromCy: 349000, margenCy: 43.0 },
              { id: 'c2', nombre: 'INMOBILIARIA LOS ANDES SPÁ', cantCy: 15, ventaCy: 5235000, netoCy: 4399160, contriCy: 1891639, pPromCy: 349000, margenCy: 43.0 }
            ]
          },
          {
            id: 'p1_v1_d2', nombre: 'Boleta Electrónica N° 45821',
            cantCy: 28, ventaCy: 9772000, ventaWow: 8725000, ventaYoy: 6980000,
            netoCy: 8211765, contriCy: 3531058, pPromCy: 349000, margenCy: 43.0,
            clientes: [
              { id: 'c3', nombre: 'CARLOS MENDOZA AGUIRRE', cantCy: 18, ventaCy: 6282000, netoCy: 5278991, contriCy: 2269966, pPromCy: 349000, margenCy: 43.0 },
              { id: 'c4', nombre: 'MARÍA JOSÉ SILVA', cantCy: 10, ventaCy: 3490000, netoCy: 2932773, contriCy: 1261092, pPromCy: 349000, margenCy: 43.0 }
            ]
          }
        ]
      },
      {
        id: 'p1_v2', nombre: 'ALEXIS CORNEJO',
        cantCy: 44, cantWow: 40, cantYoy: 35,
        ventaCy: 15356000, ventaWow: 13960000, ventaYoy: 12215000,
        netoCy: 12904201, contriCy: 5548806, pPromCy: 349000, margenCy: 43.0,
        documentos: [
          {
            id: 'p1_v2_d1', nombre: 'Factura Electrónica N° 18455',
            cantCy: 24, ventaCy: 8376000, ventaWow: 7678000, ventaYoy: 6631000,
            netoCy: 7038655, contriCy: 3026621, pPromCy: 349000, margenCy: 43.0,
            clientes: [
              { id: 'c5', nombre: 'INGENIERÍA Y CLIMATIZACIÓN KALT LTDA', cantCy: 24, ventaCy: 8376000, netoCy: 7038655, contriCy: 3026621, pPromCy: 349000, margenCy: 43.0 }
            ]
          },
          {
            id: 'p1_v2_d2', nombre: 'Boleta Electrónica N° 45890',
            cantCy: 20, ventaCy: 6980000, ventaWow: 6282000, ventaYoy: 5584000,
            netoCy: 5865546, contriCy: 2522185, pPromCy: 349000, margenCy: 43.0,
            clientes: [
              { id: 'c6', nombre: 'RODRIGO FUENZALIDA', cantCy: 20, ventaCy: 6980000, netoCy: 5865546, contriCy: 2522185, pPromCy: 349000, margenCy: 43.0 }
            ]
          }
        ]
      },
      {
        id: 'p1_v3', nombre: 'VENTA AUTOMÁTICA D2C (SHOPIFY)',
        cantCy: 30, cantWow: 28, cantYoy: 25,
        ventaCy: 10470000, ventaWow: 9772000, ventaYoy: 8725000,
        netoCy: 8798319, contriCy: 3783277, pPromCy: 349000, margenCy: 43.0,
        documentos: [
          {
            id: 'p1_v3_d1', nombre: 'Boleta Electrónica N° 45912 (E-Commerce)',
            cantCy: 30, ventaCy: 10470000, ventaWow: 9772000, ventaYoy: 8725000,
            netoCy: 8798319, contriCy: 3783277, pPromCy: 349000, margenCy: 43.0,
            clientes: [
              { id: 'c7', nombre: 'CLIENTES VARIOS WEB CHILE', cantCy: 30, ventaCy: 10470000, netoCy: 8798319, contriCy: 3783277, pPromCy: 349000, margenCy: 43.0 }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'p2',
    sku: 'KLBC0090',
    nombre: 'BOMBA DE CALOR INVERTER PISCINA POOLTEMP 12KW',
    categoria: '♨️ Bombas de Calor',
    cantCy: 28, cantWow: 22, cantYoy: 18,
    ventaCy: 44520000, ventaWow: 34980000, ventaYoy: 28620000,
    netoCy: 37411765, netoYoy: 24050420, contriCy: 16835294, contriYoy: 10582185,
    pPromCy: 1590000, pPromWow: 1590000, pPromYoy: 1590000, margenCy: 45.0, margenYoy: 44.0,
    vendedores: [
      {
        id: 'p2_v1', nombre: 'DIANA LEÓN',
        cantCy: 18, cantWow: 14, cantYoy: 10,
        ventaCy: 28620000, ventaWow: 22260000, ventaYoy: 15900000,
        netoCy: 24050420, contriCy: 10822689, pPromCy: 1590000, margenCy: 45.0,
        documentos: [
          {
            id: 'p2_v1_d1', nombre: 'Factura Electrónica N° 18510',
            cantCy: 12, ventaCy: 19080000, ventaWow: 14840000, ventaYoy: 10600000,
            netoCy: 16033613, contriCy: 7215126, pPromCy: 1590000, margenCy: 45.0,
            clientes: [
              { id: 'c8', nombre: 'CONSTRUCTORA Y PISCINAS CHILE SPÁ', cantCy: 12, ventaCy: 19080000, netoCy: 16033613, contriCy: 7215126, pPromCy: 1590000, margenCy: 45.0 }
            ]
          },
          {
            id: 'p2_v1_d2', nombre: 'Boleta Electrónica N° 45999',
            cantCy: 6, ventaCy: 9540000, ventaWow: 7420000, ventaYoy: 5300000,
            netoCy: 8016807, contriCy: 3607563, pPromCy: 1590000, margenCy: 45.0,
            clientes: [
              { id: 'c9', nombre: 'ALFREDO TAPIA BUSTAMANTE', cantCy: 6, ventaCy: 9540000, netoCy: 8016807, contriCy: 3607563, pPromCy: 1590000, margenCy: 45.0 }
            ]
          }
        ]
      },
      {
        id: 'p2_v2', nombre: 'WILLIAM GARRIDO',
        cantCy: 10, cantWow: 8, cantYoy: 8,
        ventaCy: 15900000, ventaWow: 12720000, ventaYoy: 12720000,
        netoCy: 13361345, contriCy: 6012605, pPromCy: 1590000, margenCy: 45.0,
        documentos: [
          {
            id: 'p2_v2_d1', nombre: 'Factura Electrónica N° 18522',
            cantCy: 10, ventaCy: 15900000, ventaWow: 12720000, ventaYoy: 12720000,
            netoCy: 13361345, contriCy: 6012605, pPromCy: 1590000, margenCy: 45.0,
            clientes: [
              { id: 'c10', nombre: 'HOTEL & SPA CHICUREO', cantCy: 10, ventaCy: 15900000, netoCy: 13361345, contriCy: 6012605, pPromCy: 1590000, margenCy: 45.0 }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'p3',
    sku: 'KLTM0049',
    nombre: 'TERMO ELÉCTRICO QUALITAT AI 100 LTS',
    categoria: '🚿 Termos Eléctricos',
    cantCy: 85, cantWow: 78, cantYoy: 62,
    ventaCy: 27965000, ventaWow: 25662000, ventaYoy: 20398000,
    netoCy: 23500000, netoYoy: 17141176, contriCy: 9635000, contriYoy: 6856470,
    pPromCy: 329000, pPromWow: 329000, pPromYoy: 329000, margenCy: 41.0, margenYoy: 40.0,
    vendedores: [
      {
        id: 'p3_v1', nombre: 'ALEXIS CORNEJO',
        cantCy: 50, cantWow: 45, cantYoy: 38,
        ventaCy: 16450000, ventaWow: 14805000, ventaYoy: 12502000,
        netoCy: 13823529, contriCy: 5667647, pPromCy: 329000, margenCy: 41.0,
        documentos: [
          {
            id: 'p3_v1_d1', nombre: 'Factura Electrónica N° 18600',
            cantCy: 35, ventaCy: 11515000, ventaWow: 10363500, ventaYoy: 8751400,
            netoCy: 9676471, contriCy: 3967353, pPromCy: 329000, margenCy: 41.0,
            clientes: [
              { id: 'c11', nombre: 'DISTRIBUIDORA SAN FRANCISCO LTDA', cantCy: 35, ventaCy: 11515000, netoCy: 9676471, contriCy: 3967353, pPromCy: 329000, margenCy: 41.0 }
            ]
          },
          {
            id: 'p3_v1_d2', nombre: 'Boleta Electrónica N° 46102',
            cantCy: 15, ventaCy: 4935000, ventaWow: 4441500, ventaYoy: 3750600,
            netoCy: 4147058, contriCy: 1700294, pPromCy: 329000, margenCy: 41.0,
            clientes: [
              { id: 'c12', nombre: 'GUSTAVO MORALES BENÍTEZ', cantCy: 15, ventaCy: 4935000, netoCy: 4147058, contriCy: 1700294, pPromCy: 329000, margenCy: 41.0 }
            ]
          }
        ]
      },
      {
        id: 'p3_v2', nombre: 'WILLIAM GARRIDO',
        cantCy: 35, cantWow: 33, cantYoy: 24,
        ventaCy: 11515000, ventaWow: 10857000, ventaYoy: 7896000,
        netoCy: 9676471, contriCy: 3967353, pPromCy: 329000, margenCy: 41.0,
        documentos: [
          {
            id: 'p3_v2_d1', nombre: 'Factura Electrónica N° 18644',
            cantCy: 35, ventaCy: 11515000, ventaWow: 10857000, ventaYoy: 7896000,
            netoCy: 9676471, contriCy: 3967353, pPromCy: 329000, margenCy: 41.0,
            clientes: [
              { id: 'c13', nombre: 'CONSTRUCTORA ACONCAGUA', cantCy: 35, ventaCy: 11515000, netoCy: 9676471, contriCy: 3967353, pPromCy: 329000, margenCy: 41.0 }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'p4',
    sku: 'KLPB0019',
    nombre: 'PISCINA ESTRUCTURAL RECTANGULAR 400X200X100 CM',
    categoria: '🏊 Piscinas Estructurales',
    cantCy: 52, cantWow: 45, cantYoy: 38,
    ventaCy: 25948000, ventaWow: 22455000, ventaYoy: 18962000,
    netoCy: 21805042, netoYoy: 15934454, contriCy: 8503966, contriYoy: 6055092,
    pPromCy: 499000, pPromWow: 499000, pPromYoy: 499000, margenCy: 39.0, margenYoy: 38.0,
    vendedores: [
      {
        id: 'p4_v1', nombre: 'DIANA LEÓN',
        cantCy: 32, cantWow: 28, cantYoy: 22,
        ventaCy: 15968000, ventaWow: 13972000, ventaYoy: 10978000,
        netoCy: 13418487, contriCy: 5233210, pPromCy: 499000, margenCy: 39.0,
        documentos: [
          {
            id: 'p4_v1_d1', nombre: 'Boleta Electrónica N° 46250',
            cantCy: 32, ventaCy: 15968000, ventaWow: 13972000, ventaYoy: 10978000,
            netoCy: 13418487, contriCy: 5233210, pPromCy: 499000, margenCy: 39.0,
            clientes: [
              { id: 'c14', nombre: 'PATRICIO SOTO CORVALÁN', cantCy: 32, ventaCy: 15968000, netoCy: 13418487, contriCy: 5233210, pPromCy: 499000, margenCy: 39.0 }
            ]
          }
        ]
      },
      {
        id: 'p4_v2', nombre: 'VENTA AUTOMÁTICA D2C (SHOPIFY)',
        cantCy: 20, cantWow: 17, cantYoy: 16,
        ventaCy: 9980000, ventaWow: 8483000, ventaYoy: 7984000,
        netoCy: 8386555, contriCy: 3270756, pPromCy: 499000, margenCy: 39.0,
        documentos: [
          {
            id: 'p4_v2_d1', nombre: 'Boleta Electrónica N° 46300 (E-Commerce)',
            cantCy: 20, ventaCy: 9980000, ventaWow: 8483000, ventaYoy: 7984000,
            netoCy: 8386555, contriCy: 3270756, pPromCy: 499000, margenCy: 39.0,
            clientes: [
              { id: 'c15', nombre: 'CLIENTES D2C MERCADOLIBRE / WEB', cantCy: 20, ventaCy: 9980000, netoCy: 8386555, contriCy: 3270756, pPromCy: 499000, margenCy: 39.0 }
            ]
          }
        ]
      }
    ]
  }
];

export const STOCK_DATA: StockItem[] = [
  // Calefacción
  { sku: 'KLES0087', producto: 'ESTUFA INFRARROJA EIGER 1500W WIFI', casaMatriz: 48, bodegaFull: 22, showroom: 4, totalStock: 74, venta14d: 38, ventaDiariaProm: 2.71, diasCobertura: 27.3, estado: '🟢', costoUnit: 145000, valorInventario: 10730000, categoria: '🔥 Calefacción' },
  { sku: 'KLES0088', producto: 'ESTUFA PANELES MICA WALLY 2000W', casaMatriz: 6, bodegaFull: 2, showroom: 1, totalStock: 9, venta14d: 22, ventaDiariaProm: 1.57, diasCobertura: 5.7, estado: '🔴', costoUnit: 89000, valorInventario: 801000, categoria: '🔥 Calefacción' },
  { sku: 'KLES0089', producto: 'ESTUFA OLEOELÉCTRICA KRONOS 2500W', casaMatriz: 20, bodegaFull: 12, showroom: 3, totalStock: 35, venta14d: 14, ventaDiariaProm: 1.0, diasCobertura: 35.0, estado: '🟢', costoUnit: 95000, valorInventario: 3325000, categoria: '🔥 Calefacción' },
  { sku: 'KLES0090', producto: 'CALEFACTOR CERÁMICO TORRE OSCILANTE 2000W', casaMatriz: 10, bodegaFull: 6, showroom: 2, totalStock: 18, venta14d: 16, ventaDiariaProm: 1.14, diasCobertura: 15.8, estado: '🟡', costoUnit: 62000, valorInventario: 1116000, categoria: '🔥 Calefacción' },
  { sku: 'KLES0091', producto: 'CONVECTOR DIGITAL PARED APOLO 1500W', casaMatriz: 15, bodegaFull: 7, showroom: 2, totalStock: 24, venta14d: 12, ventaDiariaProm: 0.86, diasCobertura: 28.0, estado: '🟢', costoUnit: 78000, valorInventario: 1872000, categoria: '🔥 Calefacción' },
  { sku: 'KLES0092', producto: 'ESTUFA INFRARROJA MINI EIGER 800W', casaMatriz: 0, bodegaFull: 0, showroom: 0, totalStock: 0, venta14d: 10, ventaDiariaProm: 0.71, diasCobertura: 0.0, estado: '🔴 QUIEBRE', costoUnit: 42000, valorInventario: 0, categoria: '🔥 Calefacción' },

  // Bombas de Calor
  { sku: 'KLBC0090', producto: 'BOMBA DE CALOR POOLTEMP 12KW INVERTER', casaMatriz: 14, bodegaFull: 8, showroom: 2, totalStock: 24, venta14d: 12, ventaDiariaProm: 0.86, diasCobertura: 28.0, estado: '🟢', costoUnit: 620000, valorInventario: 14880000, categoria: '♨️ Bombas de Calor' },
  { sku: 'KLBC0089', producto: 'BOMBA DE CALOR POOLTEMP 9KW', casaMatriz: 0, bodegaFull: 0, showroom: 0, totalStock: 0, venta14d: 8, ventaDiariaProm: 0.57, diasCobertura: 0.0, estado: '🔴 QUIEBRE', costoUnit: 480000, valorInventario: 0, categoria: '♨️ Bombas de Calor' },
  { sku: 'KLBC0091', producto: 'BOMBA DE CALOR POOLTEMP 15KW INVERTER', casaMatriz: 6, bodegaFull: 4, showroom: 1, totalStock: 11, venta14d: 7, ventaDiariaProm: 0.5, diasCobertura: 22.0, estado: '🟢', costoUnit: 790000, valorInventario: 8690000, categoria: '♨️ Bombas de Calor' },
  { sku: 'KLBC0092', producto: 'BOMBA DE CALOR POOLTEMP 21KW MONOFÁSICA', casaMatriz: 3, bodegaFull: 2, showroom: 1, totalStock: 6, venta14d: 5, ventaDiariaProm: 0.36, diasCobertura: 16.7, estado: '🟡', costoUnit: 1150000, valorInventario: 6900000, categoria: '♨️ Bombas de Calor' },
  { sku: 'KLBC0093', producto: 'BOMBA DE CALOR DOMÉSTICA ACS SANITARIA 200L', casaMatriz: 8, bodegaFull: 5, showroom: 2, totalStock: 15, venta14d: 9, ventaDiariaProm: 0.64, diasCobertura: 23.4, estado: '🟢', costoUnit: 850000, valorInventario: 12750000, categoria: '♨️ Bombas de Calor' },

  // Termos Eléctricos
  { sku: 'KLTM0049', producto: 'TERMO ELÉCTRICO QUALITAT AI 100 LTS', casaMatriz: 32, bodegaFull: 14, showroom: 3, totalStock: 49, venta14d: 28, ventaDiariaProm: 2.0, diasCobertura: 24.5, estado: '🟢', costoUnit: 125000, valorInventario: 6125000, categoria: '🚿 Termos Eléctricos' },
  { sku: 'KLTM0050', producto: 'TERMO ELÉCTRICO QUALITAT AI 120 LTS', casaMatriz: 11, bodegaFull: 5, showroom: 1, totalStock: 17, venta14d: 18, ventaDiariaProm: 1.29, diasCobertura: 13.2, estado: '🟡', costoUnit: 148000, valorInventario: 2516000, categoria: '🚿 Termos Eléctricos' },
  { sku: 'KLTM0051', producto: 'TERMO ELÉCTRICO QUALITAT SLIM 50 LTS', casaMatriz: 18, bodegaFull: 8, showroom: 2, totalStock: 28, venta14d: 20, ventaDiariaProm: 1.43, diasCobertura: 19.6, estado: '🟢', costoUnit: 89000, valorInventario: 2492000, categoria: '🚿 Termos Eléctricos' },
  { sku: 'KLTM0052', producto: 'TERMO ELÉCTRICO QUALITAT DIGITAL 80 LTS', casaMatriz: 21, bodegaFull: 8, showroom: 2, totalStock: 31, venta14d: 22, ventaDiariaProm: 1.57, diasCobertura: 19.7, estado: '🟢', costoUnit: 108000, valorInventario: 3348000, categoria: '🚿 Termos Eléctricos' },
  { sku: 'KLTM0053', producto: 'TERMO ELÉCTRICO COMPACT 30 LTS', casaMatriz: 7, bodegaFull: 4, showroom: 1, totalStock: 12, venta14d: 14, ventaDiariaProm: 1.0, diasCobertura: 12.0, estado: '🟡', costoUnit: 68000, valorInventario: 816000, categoria: '🚿 Termos Eléctricos' },

  // Piscinas Estructurales
  { sku: 'KLPB0019', producto: 'PISCINA ESTRUCTURAL RECTANGULAR 400X200 CM', casaMatriz: 28, bodegaFull: 12, showroom: 2, totalStock: 42, venta14d: 16, ventaDiariaProm: 1.14, diasCobertura: 36.8, estado: '🟢', costoUnit: 210000, valorInventario: 8820000, categoria: '🏊 Piscinas Estructurales' },
  { sku: 'KLPB0020', producto: 'PISCINA ESTRUCTURAL REDONDA 366X122 CM', casaMatriz: 8, bodegaFull: 3, showroom: 1, totalStock: 12, venta14d: 14, ventaDiariaProm: 1.0, diasCobertura: 12.0, estado: '🟡', costoUnit: 185000, valorInventario: 2220000, categoria: '🏊 Piscinas Estructurales' },
  { sku: 'KLPB0021', producto: 'PISCINA ESTRUCTURAL ULTRA XTR 549X274 CM', casaMatriz: 5, bodegaFull: 2, showroom: 1, totalStock: 8, venta14d: 6, ventaDiariaProm: 0.43, diasCobertura: 18.6, estado: '🟢', costoUnit: 380000, valorInventario: 3040000, categoria: '🏊 Piscinas Estructurales' },
  { sku: 'KLPB0022', producto: 'PISCINA ESTRUCTURAL FAMILIAR 300X200 CM', casaMatriz: 14, bodegaFull: 6, showroom: 2, totalStock: 22, venta14d: 18, ventaDiariaProm: 1.29, diasCobertura: 17.1, estado: '🟢', costoUnit: 145000, valorInventario: 3190000, categoria: '🏊 Piscinas Estructurales' },
  { sku: 'KLPB0023', producto: 'PISCINA INFLABLE EASY SET 305X76 CM', casaMatriz: 12, bodegaFull: 5, showroom: 2, totalStock: 19, venta14d: 15, ventaDiariaProm: 1.07, diasCobertura: 17.7, estado: '🟢', costoUnit: 52000, valorInventario: 988000, categoria: '🏊 Piscinas Estructurales' },
];

export const PENDING_DISPATCH_DATA: PendingDispatchItem[] = [
  { id: '1', documento: 'Factura Electrónica N° 58421', cliente: 'CONSTRUCTORA SANTA FE SPAN', vendedor: 'WILLIAM GARRIDO', fechaEmision: '2026-07-18', diasPendiente: 11, monto: 14250000, estado: '⏳ Pendiente', motivo: 'Sin guía asociada' },
  { id: '2', documento: 'Boleta Electrónica N° 102941', cliente: 'RODRIGO FUENZALIDA SILVA', vendedor: 'ALEXIS CORNEJO', fechaEmision: '2026-07-21', diasPendiente: 8, monto: 1590000, estado: '⏳ Pendiente', motivo: 'Guía con costo $0' },
  { id: '3', documento: 'Factura Electrónica N° 58392', cliente: 'INMOBILIARIA LOS ALERCES', vendedor: 'DIANA LEON', fechaEmision: '2026-07-22', diasPendiente: 7, monto: 8940000, estado: '⏳ Pendiente', motivo: 'Sin guía asociada' },
  { id: '4', documento: 'Boleta Electrónica N° 103112', cliente: 'MARÍA JOSEFINA CORREA', vendedor: 'WILLIAM GARRIDO', fechaEmision: '2026-07-25', diasPendiente: 4, monto: 499000, estado: '⏳ Pendiente', motivo: 'Sin guía asociada' },
  { id: '5', documento: 'Factura Electrónica N° 58440', cliente: 'CLIMATIZACIÓN BIOBÍO S.A.', vendedor: 'ALEXIS CORNEJO', fechaEmision: '2026-07-24', diasPendiente: 5, monto: 6720000, estado: '⏳ Pendiente', motivo: 'Sin guía asociada' },
  { id: '6', documento: 'Factura Electrónica N° 58455', cliente: 'INGENIERÍA Y SERVICIOS KROHN', vendedor: 'DIANA LEON', fechaEmision: '2026-07-26', diasPendiente: 3, monto: 3180000, estado: '⏳ Pendiente', motivo: 'Guía con costo $0' },
  { id: '7', documento: 'Boleta Electrónica N° 102800', cliente: 'GONZALO VALDÉS LEIVA', vendedor: 'ANDESGEAR', fechaEmision: '2026-07-15', diasPendiente: 14, monto: 349000, estado: '✅ Despachado', motivo: 'Entregado OK' }
];

export const CREDIT_NOTES_DATA: CreditNoteItem[] = [
  { id: 'nc1', documento: 'Nota de Crédito N° 4102', cliente: 'ALBERTO SCHMIDT Y CÍA', vendedor: 'WILLIAM GARRIDO', fechaEmision: '2026-06-28', fechaCaida: '2026-07-18', diasDesfase: 20, monto: 2450000, alerta: true },
  { id: 'nc2', documento: 'Nota de Crédito N° 4118', cliente: 'COMERCIAL EL ROBLE', vendedor: 'ALEXIS CORNEJO', fechaEmision: '2026-07-02', fechaCaida: '2026-07-24', diasDesfase: 22, monto: 1820000, alerta: true },
  { id: 'nc3', documento: 'Nota de Crédito N° 4125', cliente: 'PATRICIO AYLWIN B.', vendedor: 'DIANA LEON', fechaEmision: '2026-07-12', fechaCaida: '2026-07-28', diasDesfase: 16, monto: 499000, alerta: true },
  { id: 'nc4', documento: 'Nota de Crédito N° 4130', cliente: 'TERMOMECÁNICA CHILE', vendedor: 'WILLIAM GARRIDO', fechaEmision: '2026-07-20', fechaCaida: '2026-07-22', diasDesfase: 2, monto: 3290000, alerta: false }
];

export const FULFILLMENT_PROGRAMS: FulfillmentProgram[] = [
  { codigo: 'FBF', canal: 'FALABELLA', nombre: 'Falabella Fulfillment', monto: 24800000, color: '#30D158' },
  { codigo: 'FBM', canal: 'MERCADOLIBRE', nombre: 'Mercado Libre Full', monto: 22400000, color: '#FF9F0A' },
  { codigo: 'FBP', canal: 'PARIS', nombre: 'Paris Fulfillment', monto: 11200000, color: '#0A84FF' },
  { codigo: 'FBR', canal: 'RIPLEY', nombre: 'Ripley Fulfillment', monto: 9800000, color: '#5E5CE6' }
];

export const ENVIAME_SHIPMENTS: EnviameShipment[] = [
  { id: 'e1', ref: 'ENV-19584', cliente: 'KAREN TORRES', telefono: '+56981234567', comuna: 'Las Condes', direccion: 'Av. Apoquindo 4800', courier: 'BlueExpress', estado: 'ENTREGADO', costoEnvio: 4850, trackingNumber: 'BX-98123041', trackingUrl: 'https://blue.cl/tracking', esIncidencia: false, fechaCreacion: '2026-07-26' },
  { id: 'e2', ref: 'ENV-19589', cliente: 'HERNÁN PÉREZ', telefono: '+56976543210', comuna: 'Providencia', direccion: 'Pedro de Valdivia 120', courier: 'Starken', estado: 'EN TRÁNSITO', costoEnvio: 5200, trackingNumber: 'ST-4412093', trackingUrl: 'https://starken.cl/tracking', esIncidencia: false, fechaCreacion: '2026-07-27' },
  { id: 'e3', ref: 'ENV-19592', cliente: 'CLAUDIA PINTO', telefono: '+56991122334', comuna: 'Colina / Chicureo', direccion: 'Av. Chicureo 3200', courier: 'Chilexpress', estado: 'INCIDENCIA - DIRECCIÓN INCORRECTA', costoEnvio: 6800, trackingNumber: 'CX-8812390', trackingUrl: 'https://chilexpress.cl/tracking', esIncidencia: true, fechaCreacion: '2026-07-25' },
  { id: 'e4', ref: 'ENV-19601', cliente: 'FELIPE TAPIA', telefono: '+56955443322', comuna: 'Lo Barnechea', direccion: 'El Huinganal 1450', courier: 'BlueExpress', estado: 'INCIDENCIA - RETRASO COURIER', costoEnvio: 5400, trackingNumber: 'BX-9812499', trackingUrl: 'https://blue.cl/tracking', esIncidencia: true, fechaCreacion: '2026-07-24' }
];

export const LEADS_DATA: LeadItem[] = [
  { id: 'l1', fecha: '2026-07-28', semana: 30, semanaLbl: 'S30', mesNum: 7, mesLbl: 'Jul', fuente: 'Google', canal: 'WhatsApp', estado: 'CON VENTA', vendedor: 'WILLIAM GARRIDO', calificacion: 5, calificacionLbl: '⭐ 5', comuna: 'Las Condes', categoriaInteres: 'Bomba de Calor', nombre: 'Ricardo Arancibia' },
  { id: 'l2', fecha: '2026-07-28', semana: 30, semanaLbl: 'S30', mesNum: 7, mesLbl: 'Jul', fuente: 'Facebook', canal: 'Chat Web', estado: 'EN PROGRESO', vendedor: 'ALEXIS CORNEJO', calificacion: 4, calificacionLbl: '⭐ 4', comuna: 'Lo Barnechea', categoriaInteres: 'Calefacción / Estufas', nombre: 'Camila Zúñiga' },
  { id: 'l3', fecha: '2026-07-27', semana: 30, semanaLbl: 'S30', mesNum: 7, mesLbl: 'Jul', fuente: 'Instagram', canal: 'WhatsApp', estado: 'NUEVO', vendedor: 'DIANA LEON', calificacion: 3, calificacionLbl: '⭐ 3', comuna: 'Vitacura', categoriaInteres: 'Temperado de Piscina', nombre: 'Sebastián Larraín' },
  { id: 'l4', fecha: '2026-07-26', semana: 30, semanaLbl: 'S30', mesNum: 7, mesLbl: 'Jul', fuente: 'kaltemp.cl', canal: 'Chat Web', estado: 'SIN VENTA', vendedor: 'ANDESGEAR', calificacion: 2, calificacionLbl: '⭐ 2', comuna: 'Providencia', categoriaInteres: 'Termos / ACS', nombre: 'Ignacio Silva' }
];

export const ABANDONED_CARTS_DATA: AbandonedCart[] = [
  { id: 'cart_101', fecha: '2026-07-28 14:22', fechaDia: '2026-07-28', producto: 'ESTUFA INFRARROJA EIGER 1500W WIFI', sku: 'KLES0087', categoria: 'Calefacción', precioUnitario: 349000, totalPrice: 349000, estado: 'ABANDONADO', cliente: 'Felipe Araya' },
  { id: 'cart_102', fecha: '2026-07-28 11:05', fechaDia: '2026-07-28', producto: 'BOMBA DE CALOR POOLTEMP 12KW INVERTER', sku: 'KLBC0090', categoria: 'Temperado de Piscina', precioUnitario: 1590000, totalPrice: 1590000, estado: 'ABANDONADO', cliente: 'Constanza Bravo' },
  { id: 'cart_103', fecha: '2026-07-27 18:40', fechaDia: '2026-07-27', producto: 'TERMO ELÉCTRICO QUALITAT AI 100 LTS', sku: 'KLTM0049', categoria: 'BC Agua Sanitaria', precioUnitario: 329000, totalPrice: 329000, estado: 'RECUPERADO', cliente: 'Matías Orellana' },
  { id: 'cart_104', fecha: '2026-07-27 09:12', fechaDia: '2026-07-27', producto: 'PISCINA ESTRUCTURAL 400X200 CM', sku: 'KLPB0019', categoria: 'Temperado de Piscina', precioUnitario: 499000, totalPrice: 499000, estado: 'ABANDONADO', cliente: 'Daniela Montes' }
];

export const D2C_CATEGORY_PERF: D2CCategoryPerf[] = [
  { categoria: 'Calefacción', inversion: 14500000, inversionYoy: 11200000, venta: 49558000, ventaYoy: 38390000, ordenes: 142, ordenesYoy: 110, tkp: 349000, tkpYoy: 349000, tacos: 29.2, tacosYoy: 29.17 },
  { categoria: 'Temperado de Piscina', inversion: 9800000, inversionYoy: 7500000, venta: 44520000, ventaYoy: 28620000, ordenes: 28, ordenesYoy: 18, tkp: 1590000, tkpYoy: 1590000, tacos: 22.0, tacosYoy: 26.2 },
  { categoria: 'BC Agua Sanitaria', inversion: 6200000, inversionYoy: 4800000, venta: 27965000, ventaYoy: 20398000, ordenes: 85, ordenesYoy: 62, tkp: 329000, tkpYoy: 329000, tacos: 22.1, tacosYoy: 23.5 },
  { categoria: 'Generadores', inversion: 4200000, inversionYoy: 3100000, venta: 18450000, ventaYoy: 14200000, ordenes: 41, ordenesYoy: 32, tkp: 450000, tkpYoy: 443750, tacos: 22.7, tacosYoy: 21.8 },
  { categoria: 'BC Calefacción', inversion: 3800000, inversionYoy: 2900000, venta: 16800000, ventaYoy: 12500000, ordenes: 12, ordenesYoy: 9, tkp: 1400000, tkpYoy: 1388888, tacos: 22.6, tacosYoy: 23.2 },
  { categoria: 'Pmax / brand', inversion: 5400000, inversionYoy: 4100000, venta: 22400000, ventaYoy: 18900000, ordenes: 64, ordenesYoy: 54, tkp: 350000, tkpYoy: 350000, tacos: 24.1, tacosYoy: 21.6 }
];

export const CAMPAIGNS_DATA: CampaignItem[] = [
  { id: 'c1', campana: 'CL_Google_Search_Inverter_Heating', plataforma: 'Google', gastoCy: 12450000, gastoWow: 11200000, gastoYoy: 9800000, impresionesCy: 480000, impresionesWow: 420000, impresionesYoy: 390000, clicsCy: 21600, clicsWow: 18900, clicsYoy: 17160, ctrCy: 4.5, ctrWow: 4.5, ctrYoy: 4.4, roasCy: 4.25, roasWow: 4.10, roasYoy: 3.90, valorComprasCy: 52912500 },
  { id: 'c2', campana: 'CL_Meta_Sales_Calefaccion_Eiger', plataforma: 'Meta', gastoCy: 9800000, gastoWow: 8900000, gastoYoy: 7500000, impresionesCy: 890000, impresionesWow: 780000, impresionesYoy: 680000, clicsCy: 16020, clicsWow: 14040, clicsYoy: 12240, ctrCy: 1.8, ctrWow: 1.8, ctrYoy: 1.8, roasCy: 3.80, roasWow: 3.65, roasYoy: 3.40, valorComprasCy: 37240000 },
  { id: 'c3', campana: 'CL_Google_PerformanceMax_PoolTemp', plataforma: 'Google', gastoCy: 8200000, gastoWow: 7500000, gastoYoy: 6200000, impresionesCy: 350000, impresionesWow: 310000, impresionesYoy: 260000, clicsCy: 12250, clicsWow: 10850, clicsYoy: 9100, ctrCy: 3.5, ctrWow: 3.5, ctrYoy: 3.5, roasCy: 4.80, roasWow: 4.60, roasYoy: 4.20, valorComprasCy: 39360000 },
  { id: 'c4', campana: 'CL_Meta_Retargeting_Carros_Abandonados', plataforma: 'Meta', gastoCy: 4500000, gastoWow: 3900000, gastoYoy: 3200000, impresionesCy: 210000, impresionesWow: 180000, impresionesYoy: 150000, clicsCy: 5250, clicsWow: 4500, clicsYoy: 3750, ctrCy: 2.5, ctrWow: 2.5, ctrYoy: 2.5, roasCy: 6.20, roasWow: 5.90, roasYoy: 5.50, valorComprasCy: 27900000 }
];

export const DISTRIBUTORS_DATA: DistributorItem[] = [
  { id: 'd1', cliente: 'TERMOMECÁNICA S.A.', categoria: 'Calefacción', producto: 'ESTUFA INFRARROJA EIGER 1500W', v2024: 18500000, c2024: 53, v2025: 22400000, c2025: 64, v2026: 28900000, c2026: 82, yoyPct: 29.0 },
  { id: 'd2', cliente: 'HIDROCLIMA CHILE LTDA', categoria: 'Bombas de Calor', producto: 'BOMBA DE CALOR POOLTEMP 12KW', v2024: 14200000, c2024: 9, v2025: 18900000, c2025: 12, v2026: 24800000, c2026: 15, yoyPct: 31.2 },
  { id: 'd3', cliente: 'CLIMATIZACIÓN DEL SUR', categoria: 'Termos Eléctricos', producto: 'TERMO QUALITAT AI 100 LTS', v2024: 11800000, c2024: 36, v2025: 14500000, c2025: 44, v2026: 18200000, c2026: 55, yoyPct: 25.5 },
  { id: 'd4', cliente: 'INGENIERÍA TÉRMICA ANDINA', categoria: 'Calefacción', producto: 'ESTUFA WALLY 2000W', v2024: 9500000, c2024: 43, v2025: 11200000, c2025: 50, v2026: 14100000, c2026: 64, yoyPct: 25.9 }
];

export const DAILY_TEMP_SALES: DailyTempSale[] = [
  { fechaStr: '2026-07-15', fechaDisp: '15/07', brutoTotal: 18200000, tempMax: 11, tempMin: 2 },
  { fechaStr: '2026-07-16', fechaDisp: '16/07', brutoTotal: 22400000, tempMax: 9, tempMin: 1 },
  { fechaStr: '2026-07-17', fechaDisp: '17/07', brutoTotal: 28900000, tempMax: 8, tempMin: 0 },
  { fechaStr: '2026-07-18', fechaDisp: '18/07', brutoTotal: 34500000, tempMax: 7, tempMin: -1 },
  { fechaStr: '2026-07-19', fechaDisp: '19/07', brutoTotal: 31200000, tempMax: 8, tempMin: 1 },
  { fechaStr: '2026-07-20', fechaDisp: '20/07', brutoTotal: 24800000, tempMax: 10, tempMin: 3 },
  { fechaStr: '2026-07-21', fechaDisp: '21/07', brutoTotal: 19500000, tempMax: 13, tempMin: 4 },
  { fechaStr: '2026-07-22', fechaDisp: '22/07', brutoTotal: 16800000, tempMax: 15, tempMin: 5 },
  { fechaStr: '2026-07-23', fechaDisp: '23/07', brutoTotal: 21400000, tempMax: 11, tempMin: 2 },
  { fechaStr: '2026-07-24', fechaDisp: '24/07', brutoTotal: 26800000, tempMax: 9, tempMin: 1 },
  { fechaStr: '2026-07-25', fechaDisp: '25/07', brutoTotal: 29500000, tempMax: 8, tempMin: 0 },
  { fechaStr: '2026-07-26', fechaDisp: '26/07', brutoTotal: 27100000, tempMax: 10, tempMin: 2 },
  { fechaStr: '2026-07-27', fechaDisp: '27/07', brutoTotal: 23200000, tempMax: 12, tempMin: 3 },
  { fechaStr: '2026-07-28', fechaDisp: '28/07', brutoTotal: 25400000, tempMax: 11, tempMin: 2 }
];
