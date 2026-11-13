//+------------------------------------------------------------------+
//| ProSignals EURUSD M15 H1 Pullback v7 - 3% DEMO EXPERIMENT     |
//| Untested in MT5. No daily-profit guarantee. Never martingale.    |
//+------------------------------------------------------------------+
#property strict
#property version "7.00"
#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpEnableDemoOrders       = false;
input double InpResearchCapitalUSD     = 100.0;
input double InpRiskPct                = 3.0;   // maximum 3% of capped demo equity
input double InpMaxDailyLossUSD        = 6.0;
input int    InpTargetWinningTrades    = 2;     // stop new entries after two wins
input int    InpMaxEntriesPerDay       = 3;
input int    InpMaxConsecutiveLosses   = 2;
input int    InpBrokerUTCOffsetHours   = 0;     // provisional; verify for actual broker and history
input int    InpUTCStartHour           = 12;    // research NY fixed-UTC proxy
input int    InpUTCEndHour             = 20;
input int    InpMaxSpreadPoints        = 15;    // 1.5 pips if EURUSD 5 digits
input double InpMaxSpreadToStop        = 0.20;
input double InpRewardR                = 2.0;
input int    InpADXMinimum             = 25;    // stricter candidate; unvalidated
input double InpATRStopMultiple        = 2.0;
input ulong  InpMagic                  = 26111307;

int hH1Fast=INVALID_HANDLE,hH1Slow=INVALID_HANDLE;
int hM15EMA=INVALID_HANDLE,hM15ADX=INVALID_HANDLE,hM15RSI=INVALID_HANDLE,hM15ATR=INVALID_HANDLE;
datetime lastBar=0;
int lockedUTCDate=0;

bool ReadValue(int handle,int buffer,int shift,double &out) {
 double arr[];
 if(CopyBuffer(handle,buffer,shift,1,arr)!=1)return false;
 out=arr[0];
 return MathIsValidNumber(out);
}
datetime UTCServerTime(datetime serverTime) {
 return serverTime-InpBrokerUTCOffsetHours*3600;
}
int UTCDate(datetime t) {
 MqlDateTime dt;TimeToStruct(t,dt);return dt.year*10000+dt.mon*100+dt.day;
}
datetime UTCMidnightAsServer() {
 MqlDateTime dt;TimeToStruct(UTCServerTime(TimeCurrent()),dt);
 dt.hour=0;dt.min=0;dt.sec=0;
 return StructToTime(dt)+InpBrokerUTCOffsetHours*3600;
}
bool OwnPosition() {
 for(int i=PositionsTotal()-1;i>=0;i--) {
   ulong id=PositionGetTicket(i);
   if(id>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
      (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;
 }
 return false;
}
double FloatingOwnPnL() {
 double pnl=0;
 for(int i=PositionsTotal()-1;i>=0;i--) {
   ulong id=PositionGetTicket(i);
   if(id>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
      (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
     pnl+=PositionGetDouble(POSITION_PROFIT)+PositionGetDouble(POSITION_SWAP);
 }
 return pnl;
}
void CloseOwnPositions() {
 for(int i=PositionsTotal()-1;i>=0;i--) {
   ulong id=PositionGetTicket(i);
   if(id>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
      (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic) {
     if(!trade.PositionClose(id))Print("Close request failed: ",trade.ResultRetcodeDescription());
     else if(trade.ResultRetcode()!=TRADE_RETCODE_DONE)
       Print("Close not confirmed: ",trade.ResultRetcodeDescription());
   }
 }
}
void DailyStats(int &entries,int &wins,int &losingStreak,double &realized) {
 entries=0;wins=0;losingStreak=0;realized=0;
 if(!HistorySelect(UTCMidnightAsServer(),TimeCurrent()))return;
 int n=HistoryDealsTotal();
 // Count deal entries, realized exits and commissions for this EA only.
 // One position at a time; no scale-ins or partial closes are programmed.
 for(int i=0;i<n;i++) {
   ulong d=HistoryDealGetTicket(i);
   if(d==0||HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol||
      (ulong)HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic)continue;
   long kind=HistoryDealGetInteger(d,DEAL_ENTRY);
   double cash=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+
      HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);
   realized+=cash;
   if(kind==DEAL_ENTRY_IN)entries++;
   if(kind==DEAL_ENTRY_OUT||kind==DEAL_ENTRY_INOUT) {
     if(cash>0)wins++;
   }
 }
 for(int i=n-1;i>=0;i--) {
   ulong d=HistoryDealGetTicket(i);
   if(d==0||HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol||
      (ulong)HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic)continue;
   long kind=HistoryDealGetInteger(d,DEAL_ENTRY);
   if(kind!=DEAL_ENTRY_OUT && kind!=DEAL_ENTRY_INOUT)continue;
   double pnl=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+
      HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);
   if(pnl<0)losingStreak++;
   else break;
 }
}
double SizedLots(int direction,double entry,double stop,double budget) {
 double expected=0;
 ENUM_ORDER_TYPE order=direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(order,_Symbol,1.0,entry,stop,expected)||expected>=0)return 0;
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 if(step<=0||minimum<=0||budget<=0)return 0;
 double lots=MathFloor(budget/(-expected)/step+1e-9)*step;
 lots=MathMin(lots,maximum);
 if(lots+1e-9<minimum)return 0;
 double margin=0;
 if(!OrderCalcMargin(order,_Symbol,lots,entry,margin)||
    margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9)return 0;
 return NormalizeDouble(lots,8);
}
// After execution, reject fills that exceed the cash-risk budget or that
// do not preserve the intended gross price-distance 1:2 risk/reward ratio.
// Broker commission/swap, gaps and stop slippage can still change realized R.
void RejectOwnFill(ulong ticket,string reason) {
 Print("v7 post-fill safety rejection: ",reason);
 if(!trade.PositionClose(ticket) ||
    trade.ResultRetcode()!=TRADE_RETCODE_DONE)
   Print("SAFETY WARNING: could not confirm close, ",trade.ResultRetcodeDescription());
}
void AuditExecutedRiskAndRR(double cashBudget) {
 ulong ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--) {
   ulong candidate=PositionGetTicket(i);
   if(candidate>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
      (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic) {
      ticket=candidate;break;
   }
 }
 if(ticket==0) {Print("SAFETY WARNING: executed position not found for audit");return;}
 long kind=PositionGetInteger(POSITION_TYPE);
 int direction=kind==POSITION_TYPE_BUY?1:-1;
 double openPrice=PositionGetDouble(POSITION_PRICE_OPEN);
 double stop=PositionGetDouble(POSITION_SL);
 double volume=PositionGetDouble(POSITION_VOLUME);
 double stopDistance=direction*(openPrice-stop);
 if(stop<=0||stopDistance<=_Point||volume<=0) {
   RejectOwnFill(ticket,"missing or incorrect stop");return;
 }
 ENUM_ORDER_TYPE order=direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double stopCash=0;
 if(!OrderCalcProfit(order,_Symbol,volume,openPrice,stop,stopCash) ||
    stopCash>=0 || -stopCash>cashBudget+1e-6) {
   RejectOwnFill(ticket,"risk exceeds allotted gross budget after fill");return;
 }
 double expectedTarget=NormalizeDouble(openPrice+direction*2.0*stopDistance,_Digits);
 double actualTarget=PositionGetDouble(POSITION_TP);
 if(direction*(expectedTarget-openPrice)<1.999*stopDistance) {
   RejectOwnFill(ticket,"target round-off below 2R");return;
 }
 if(MathAbs(actualTarget-expectedTarget)>_Point/2.0) {
   if(!trade.PositionModify(ticket,stop,expectedTarget) ||
      trade.ResultRetcode()!=TRADE_RETCODE_DONE) {
      RejectOwnFill(ticket,"could not adjust TP after slippage");return;
   }
 }
 Print("v7 POST-FILL gross risk audit pass. budget=",cashBudget,
       " expectedStopLoss=",stopCash," target=",expectedTarget);
}

int OnInit() {
 if((MQLInfoInteger(MQL_TESTER)==0 &&
     AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO) ||
    _Symbol!="EURUSD"||_Period!=PERIOD_M15) {
    Print("DEMO EURUSD M15 ONLY: refusing initialization");return INIT_PARAMETERS_INCORRECT;
 }
 if(InpRiskPct<=0||InpRiskPct>3.0||InpResearchCapitalUSD<=0||
    InpMaxDailyLossUSD<=0||InpTargetWinningTrades!=2||
    InpMaxEntriesPerDay<1||InpMaxEntriesPerDay>3||
    InpMaxConsecutiveLosses<1||InpMaxConsecutiveLosses>2||
    MathAbs(InpRewardR-2.0)>1e-8||InpATRStopMultiple<=0||
    InpMaxSpreadPoints<=0||InpMaxSpreadToStop<=0||InpMaxSpreadToStop>1||
    InpBrokerUTCOffsetHours< -12||InpBrokerUTCOffsetHours>14||
    InpUTCStartHour<0||InpUTCEndHour>24||InpUTCStartHour>=InpUTCEndHour)
    return INIT_PARAMETERS_INCORRECT;
 hH1Fast=iMA(_Symbol,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);
 hH1Slow=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);
 hM15EMA=iMA(_Symbol,PERIOD_M15,20,0,MODE_EMA,PRICE_CLOSE);
 hM15ADX=iADX(_Symbol,PERIOD_M15,14);
 hM15RSI=iRSI(_Symbol,PERIOD_M15,14,PRICE_CLOSE);
 hM15ATR=iATR(_Symbol,PERIOD_M15,14);
 if(hH1Fast==INVALID_HANDLE||hH1Slow==INVALID_HANDLE||
    hM15EMA==INVALID_HANDLE||hM15ADX==INVALID_HANDLE||
    hM15RSI==INVALID_HANDLE||hM15ATR==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);
 trade.SetDeviationInPoints(10);
 trade.SetTypeFillingBySymbol(_Symbol);
 Print("M15 H1 v7 3% 2R candidate. Research orders=",InpEnableDemoOrders);
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) {
 IndicatorRelease(hH1Fast);IndicatorRelease(hH1Slow);
 IndicatorRelease(hM15EMA);IndicatorRelease(hM15ADX);
 IndicatorRelease(hM15RSI);IndicatorRelease(hM15ATR);
}
void OnTick() {
 // Stop controls check every tick when enabled, not only on candle close.
 if(!InpEnableDemoOrders||
    (MQLInfoInteger(MQL_TESTER)==0 &&
     AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO))return;
 datetime utc=UTCServerTime(TimeCurrent());
 int day=UTCDate(utc);
 int entries,wins,streak;
 double realized;
 DailyStats(entries,wins,streak,realized);
 if(realized<=-InpMaxDailyLossUSD ||
    realized+FloatingOwnPnL()<=-InpMaxDailyLossUSD) {
    lockedUTCDate=day;CloseOwnPositions();return; // gaps can exceed the limit
 }
 if(lockedUTCDate==day||wins>=InpTargetWinningTrades||
    entries>=InpMaxEntriesPerDay||streak>=InpMaxConsecutiveLosses)return;
 datetime bar=iTime(_Symbol,PERIOD_M15,0);
 if(bar==0||bar==lastBar)return;
 lastBar=bar;
 MqlDateTime clock;TimeToStruct(utc,clock);
 if(clock.hour<InpUTCStartHour||clock.hour>=InpUTCEndHour||
    OwnPosition()||PositionSelect(_Symbol))return; // avoid netting-account interference
 if(Bars(_Symbol,PERIOD_H1)<210||Bars(_Symbol,PERIOD_M15)<60)return;
 double e50,e200,e20,adx,rsi,atr;
 if(!ReadValue(hH1Fast,0,1,e50)||!ReadValue(hH1Slow,0,1,e200)||
    !ReadValue(hM15EMA,0,1,e20)||!ReadValue(hM15ADX,0,1,adx)||
    !ReadValue(hM15RSI,0,1,rsi)||!ReadValue(hM15ATR,0,1,atr))return;
 if(atr<=0||adx<InpADXMinimum)return;
 double hClose=iClose(_Symbol,PERIOD_H1,1);
 double mClose=iClose(_Symbol,PERIOD_M15,1);
 double mPrevClose=iClose(_Symbol,PERIOD_M15,2);
 double mPrevEMA=0;
 if(!ReadValue(hM15EMA,0,2,mPrevEMA))return;
 double low5=DBL_MAX,high5=-DBL_MAX;
 for(int s=1;s<=5;s++) {
   low5=MathMin(low5,iLow(_Symbol,PERIOD_M15,s));
   high5=MathMax(high5,iHigh(_Symbol,PERIOD_M15,s));
 }
 // Closed-bar reclaim after pullback. One signal per crossover, avoiding repeat entries.
 bool buy=hClose>e200&&e50>e200&&low5<=e20&&
    mPrevClose<=mPrevEMA&&mClose>e20&&rsi>=45&&rsi<=65;
 bool sell=hClose<e200&&e50<e200&&high5>=e20&&
    mPrevClose>=mPrevEMA&&mClose<e20&&rsi>=35&&rsi<=55;
 if(buy==sell)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 int direction=buy?1:-1;
 double entry=buy?tick.ask:tick.bid;
 double distance=MathMax(InpATRStopMultiple*atr,
    buy?entry-low5:high5-entry);
 double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point+2*_Point;
 distance=MathMax(distance,minimum);
 double spread=tick.ask-tick.bid;
 if(spread>InpMaxSpreadPoints*_Point || spread>distance*InpMaxSpreadToStop)return;
 double stop=NormalizeDouble(entry-direction*distance,_Digits);
 double target=NormalizeDouble(entry+direction*InpRewardR*MathAbs(entry-stop),_Digits);
 if(MathAbs(target-entry)<1.999*MathAbs(entry-stop))return;
 double riskPct=InpRiskPct; // fixed risk cap; NO loss-recovery escalation
 double cappedEquity=MathMin(InpResearchCapitalUSD,AccountInfoDouble(ACCOUNT_EQUITY));
 double budget=cappedEquity*riskPct/100.0;
 double lots=SizedLots(direction,entry,stop,budget);
 if(lots<=0){Print("Skip: minimum tradable lot exceeds risk/margin budget");return;}
 bool ok=buy?trade.Buy(lots,_Symbol,0,stop,
    target,"ProSignals v7 M15 DEMO"):
    trade.Sell(lots,_Symbol,0,stop,
    target,"ProSignals v7 M15 DEMO");
 if(!ok||(trade.ResultRetcode()!=TRADE_RETCODE_DONE&&trade.ResultRetcode()!=TRADE_RETCODE_PLACED))
    Print("Order rejected: ",trade.ResultRetcodeDescription());
 else {
    if(trade.ResultRetcode()==TRADE_RETCODE_DONE)AuditExecutedRiskAndRR(budget);
    Print("Research entry ",buy?"BUY":"SELL"," lots=",lots,
    " spread=",spread/_Point," stopPts=",distance/_Point,
    " riskPct=",riskPct," dayEntries=",entries," realized=",realized);
 }
}
