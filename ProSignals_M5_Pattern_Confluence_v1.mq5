//+------------------------------------------------------------------+
//| ProSignals M5 Pattern Confluence EA - research / tester only       |
//| Two independent modes: sweep reversal and trend breakout retest    |
//| No guaranteed win rate. Orders disabled by default.               |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
CTrade trade;
enum PatternMode { SWEEP_REVERSAL=0, BREAKOUT_RETEST=1, BOTH=2 };
input PatternMode InpMode=BOTH;
input bool InpEnableOrders=false;
input double InpRiskPct=1.0;
input double InpRewardR=1.5;
input int InpMaxSpreadPoints=25;
input int InpStartHour=7;   // broker server time
input int InpEndHour=19;    // broker server time
input int InpMaxTradesPerDay=3;
input double InpMaxDailyLossPct=3.0;
input int InpRangeBars=20;
input int InpRetestExpiryBars=4;
input double InpSweepATRBuffer=0.10;
input double InpMinATRPoints=35;
input long InpMagic=261105;
int hFast,hSlow,hATR,hRSI,hADX;
datetime lastBar=0,dayStart=0;
double dayStartEquity=0;
int dailyEntries=0;
int pendingSide=0,pendingAge=0;
double pendingLevel=0;
int OnInit(){
 if(_Period!=PERIOD_M5) {Print("Attach to M5 chart");return INIT_PARAMETERS_INCORRECT;}
 if(InpRiskPct<=0||InpRiskPct>3||InpRewardR<=0||InpRangeBars<10||InpMaxTradesPerDay<1) return INIT_PARAMETERS_INCORRECT;
 hFast=iMA(_Symbol,PERIOD_M5,20,0,MODE_EMA,PRICE_CLOSE);
 hSlow=iMA(_Symbol,PERIOD_M5,50,0,MODE_EMA,PRICE_CLOSE);
 hATR=iATR(_Symbol,PERIOD_M5,14);
 hRSI=iRSI(_Symbol,PERIOD_M5,14,PRICE_CLOSE);
 hADX=iADX(_Symbol,PERIOD_M5,14);
 if(hFast==INVALID_HANDLE||hSlow==INVALID_HANDLE||hATR==INVALID_HANDLE||hRSI==INVALID_HANDLE||hADX==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);
 trade.SetDeviationInPoints(10);
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){IndicatorRelease(hFast);IndicatorRelease(hSlow);IndicatorRelease(hATR);IndicatorRelease(hRSI);IndicatorRelease(hADX);}
bool Val(int h,int buffer,int shift,double &v){double a[];ArraySetAsSeries(a,true);if(CopyBuffer(h,buffer,shift,1,a)!=1)return false;v=a[0];return MathIsValidNumber(v);}
bool HasPosition(){for(int i=PositionsTotal()-1;i>=0;i--){ulong ticket=PositionGetTicket(i);if(ticket>0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}return false;}
void RefreshDay(){
 MqlDateTime dt;TimeToStruct(TimeCurrent(),dt);dt.hour=0;dt.min=0;dt.sec=0;
 datetime midnight=StructToTime(dt);
 if(midnight!=dayStart){dayStart=midnight;dayStartEquity=AccountInfoDouble(ACCOUNT_EQUITY);dailyEntries=0;pendingSide=0;}
}
double Lots(int side,double entry,double sl){
 double risk=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPct/100.0;
 double loss=0;
 if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1.0,entry,sl,loss)||loss>=0)return 0;
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maxLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 if(step<=0||minLot<=0)return 0;
 double lots=MathFloor((risk/(-loss))/step)*step;
 if(lots<minLot)return 0; // never round UP above risk budget
 lots=MathMin(lots,maxLot);
 double margin=0;
 if(!OrderCalcMargin(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lots,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9)return 0;
 return NormalizeDouble(lots,8);
}
void TryOrder(int side,double sl,double atr){
 if(!InpEnableOrders||HasPosition()||dailyEntries>=InpMaxTradesPerDay)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double entry=side>0?tick.ask:tick.bid;
 double minDist=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point+2*_Point;
 double distance=MathAbs(entry-sl);
 if((side>0&&sl>=entry)||(side<0&&sl<=entry)||distance<MathMax(minDist,0.6*atr)||distance>2.5*atr)return;
 double tp=entry+side*InpRewardR*distance;
 double lots=Lots(side,entry,sl);if(lots<=0)return;
 bool ok=side>0?trade.Buy(lots,_Symbol,0,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"M5 confluence"):
 trade.Sell(lots,_Symbol,0,NormalizeDouble(sl,_Digits),NormalizeDouble(tp,_Digits),"M5 confluence");
 if(ok&&(trade.ResultRetcode()==TRADE_RETCODE_DONE||trade.ResultRetcode()==TRADE_RETCODE_PLACED))dailyEntries++;
 else Print("Order rejected: ",trade.ResultRetcodeDescription());
}
void OnTick(){
 datetime t=iTime(_Symbol,PERIOD_M5,0);
 if(t==0||t==lastBar)return;
 lastBar=t;RefreshDay();
 if(!InpEnableOrders)return;
 MqlDateTime tm;TimeToStruct(t,tm);
 if(tm.hour<InpStartHour||tm.hour>=InpEndHour)return;
 if(dayStartEquity>0&&AccountInfoDouble(ACCOUNT_EQUITY)<=dayStartEquity*(1-InpMaxDailyLossPct/100.0))return;
 if(HasPosition()||dailyEntries>=InpMaxTradesPerDay)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)||tick.ask-tick.bid>InpMaxSpreadPoints*_Point)return;
 MqlRates b[];ArraySetAsSeries(b,true);
 int count=InpRangeBars+10;
 if(CopyRates(_Symbol,PERIOD_M5,0,count,b)<count)return;
 double fast,slow,atr,rsi,adx,plusDI,minusDI;
 if(!Val(hFast,0,1,fast)||!Val(hSlow,0,1,slow)||!Val(hATR,0,1,atr)||!Val(hRSI,0,1,rsi)||!Val(hADX,0,1,adx)||!Val(hADX,1,1,plusDI)||!Val(hADX,2,1,minusDI))return;
 if(atr<InpMinATRPoints*_Point)return;
 double hi=b[2].high,lo=b[2].low;
 for(int i=3;i<InpRangeBars+2;i++){hi=MathMax(hi,b[i].high);lo=MathMin(lo,b[i].low);}
 // Breakout-retest: signal from completed candle, wait for later candle to retest.
 if((InpMode==BREAKOUT_RETEST||InpMode==BOTH)&&pendingSide!=0){
   pendingAge++;
   if(pendingAge>InpRetestExpiryBars){pendingSide=0;}
   else{
     int side=pendingSide;
     bool retest=side>0?(b[1].low<=pendingLevel+0.15*atr&&b[1].close>pendingLevel&&b[1].close>b[1].open):
                      (b[1].high>=pendingLevel-0.15*atr&&b[1].close<pendingLevel&&b[1].close<b[1].open);
     if(retest){
       double stop=side>0?MathMin(b[1].low,pendingLevel-0.5*atr):MathMax(b[1].high,pendingLevel+0.5*atr);
       pendingSide=0;TryOrder(side,stop,atr);return;
     }
   }
 }
 if(InpMode==SWEEP_REVERSAL||InpMode==BOTH){
   // Wick crosses previous 20-bar range, closes back inside; RSI confirms reversal.
   bool bull=b[1].low<lo-InpSweepATRBuffer*atr&&b[1].close>lo&&b[1].close>b[1].open&&rsi<48;
   bool bear=b[1].high>hi+InpSweepATRBuffer*atr&&b[1].close<hi&&b[1].close<b[1].open&&rsi>52;
   if(bull){TryOrder(1,b[1].low-0.1*atr,atr);return;}
   if(bear){TryOrder(-1,b[1].high+0.1*atr,atr);return;}
 }
 if(InpMode==BREAKOUT_RETEST||InpMode==BOTH){
   if(b[1].close>hi+0.12*atr&&fast>slow&&adx>=22&&plusDI>minusDI&&b[1].close>b[1].open){pendingSide=1;pendingLevel=hi;pendingAge=0;}
   else if(b[1].close<lo-0.12*atr&&fast<slow&&adx>=22&&minusDI>plusDI&&b[1].close<b[1].open){pendingSide=-1;pendingLevel=lo;pendingAge=0;}
 }
}
