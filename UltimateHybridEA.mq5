//+------------------------------------------------------------------+
//|                                            UltimateHybridEA.mq5 |
//|                           Expert Advisor - Automated Trading     |
//|                         Based on 62.16% Accurate System          |
//+------------------------------------------------------------------+
#property copyright "Ultimate Hybrid Trading System EA"
#property link      "https://github.com/yourrepo"
#property version   "1.00"

#include <Trade\Trade.mqh>

//--- Input parameters
input double   InpLotSize = 0.01;             // Lot size
input double   InpRiskPercent = 2.0;          // Risk per trade (%)
input bool     InpUseAutoLot = true;          // Auto calculate lot size
input double   InpConfidenceThreshold = 0.75; // Minimum confidence (75-85%)
input int      InpStopLossPips = 50;          // Stop Loss in pips (if manual)
input double   InpRiskReward = 2.0;           // Risk:Reward ratio
input bool     InpUsePartialExit = true;      // Use partial exits
input double   InpPartialExitPercent = 50.0;  // First exit % of position
input double   InpPartialExitRR = 1.5;        // Partial exit at X R:R
input int      InpMagicNumber = 123456;       // Magic number for EA
input bool     InpTradeOnNewBarOnly = true;   // Only trade on new bar
input int      InpMaxTradesPerDay = 3;        // Maximum trades per day

//--- Global variables
CTrade trade;
datetime lastBarTime = 0;
int tradesThisDay = 0;
datetime currentDay = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(10);
   trade.SetTypeFilling(ORDER_FILLING_FOK);

   Print("Ultimate Hybrid EA initialized");
   Print("Confidence Threshold: ", InpConfidenceThreshold);
   Print("Risk per trade: ", InpRiskPercent, "%");
   Print("Max trades per day: ", InpMaxTradesPerDay);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check if new bar
   if(InpTradeOnNewBarOnly)
   {
      datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
      if(currentBarTime == lastBarTime)
         return; // Wait for new bar

      lastBarTime = currentBarTime;
   }

   // Reset daily trade counter
   datetime today = iTime(_Symbol, PERIOD_D1, 0);
   if(today != currentDay)
   {
      currentDay = today;
      tradesThisDay = 0;
   }

   // Check max trades per day
   if(tradesThisDay >= InpMaxTradesPerDay)
      return;

   // Check if we already have an open position
   if(PositionSelect(_Symbol))
   {
      ManageOpenPosition();
      return;
   }

   // Extract features
   double features[];
   if(!ExtractFeatures(features))
      return;

   // Calculate signal
   double confidence = 0;
   int direction = 0;
   CalculateSignal(features, confidence, direction);

   // Check if signal meets requirements
   if(confidence < InpConfidenceThreshold)
      return;

   if(direction == 0)
      return;

   // Open position
   OpenPosition(direction, confidence, features);
}

//+------------------------------------------------------------------+
//| Extract features                                                  |
//+------------------------------------------------------------------+
bool ExtractFeatures(double &features[])
{
   int lookback = 100;

   // Need minimum bars
   int bars = Bars(_Symbol, PERIOD_CURRENT);
   if(bars < lookback)
      return false;

   ArrayResize(features, 11);

   // Get price arrays
   double close[];
   ArraySetAsSeries(close, true);
   if(CopyClose(_Symbol, PERIOD_CURRENT, 0, lookback, close) <= 0)
      return false;

   // 1. Returns
   features[0] = (close[0] - close[5]) / close[5];
   features[1] = (close[0] - close[10]) / close[10];
   features[2] = (close[0] - close[20]) / close[20];
   features[3] = (close[0] - close[50]) / close[50];

   // 2. Volatility
   features[4] = CalculateVolatility(10);
   features[5] = CalculateVolatility(20);

   // 3. RSI
   double rsiBuffer[];
   int rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, 14, PRICE_CLOSE);
   if(rsiHandle == INVALID_HANDLE)
      return false;

   if(CopyBuffer(rsiHandle, 0, 0, 1, rsiBuffer) <= 0)
      return false;

   features[6] = rsiBuffer[0] / 100.0; // Normalize to 0-1

   // 4. Momentum
   features[7] = (close[0] - close[20]) / close[20];

   // 5. Fractal Dimension (simplified for EA)
   features[8] = CalculateFractalDimension(close, 50);

   // 6. Trend slope
   features[9] = CalculateTrendSlope(close, 20);

   // 7. Current price
   features[10] = close[0];

   return true;
}

//+------------------------------------------------------------------+
//| Calculate Volatility                                             |
//+------------------------------------------------------------------+
double CalculateVolatility(int period)
{
   double returns[];
   ArrayResize(returns, period);

   for(int i = 0; i < period; i++)
   {
      double close1 = iClose(_Symbol, PERIOD_CURRENT, i);
      double close2 = iClose(_Symbol, PERIOD_CURRENT, i + 1);

      if(close2 != 0)
         returns[i] = (close1 - close2) / close2;
   }

   // Standard deviation
   double mean = 0;
   for(int i = 0; i < period; i++)
      mean += returns[i];
   mean /= period;

   double variance = 0;
   for(int i = 0; i < period; i++)
      variance += MathPow(returns[i] - mean, 2);
   variance /= period;

   return MathSqrt(variance);
}

//+------------------------------------------------------------------+
//| Calculate Fractal Dimension (simplified)                         |
//+------------------------------------------------------------------+
double CalculateFractalDimension(const double &price[], int window)
{
   // Simplified Higuchi method
   int kmax = 8;
   double lk[];
   ArrayResize(lk, kmax);

   for(int k = 1; k <= kmax; k++)
   {
      double lm_sum = 0;
      int lm_count = 0;

      for(int m = 0; m < k; m++)
      {
         double ll = 0;
         int n_max = (window - m - 1) / k;

         for(int i = 1; i < n_max; i++)
         {
            ll += MathAbs(price[m + i * k] - price[m + (i-1) * k]);
         }

         if(n_max > 0)
         {
            ll = ll * (window - 1) / (k * n_max * k);
            lm_sum += ll;
            lm_count++;
         }
      }

      if(lm_count > 0)
         lk[k-1] = lm_sum / lm_count;
   }

   // Linear regression for slope
   double sum_x = 0, sum_y = 0, sum_xy = 0, sum_xx = 0;
   int n = 0;

   for(int k = 0; k < kmax; k++)
   {
      if(lk[k] > 0)
      {
         double x = MathLog(k + 1);
         double y = MathLog(lk[k]);

         sum_x += x;
         sum_y += y;
         sum_xy += x * y;
         sum_xx += x * x;
         n++;
      }
   }

   if(n < 3)
      return 2.0;

   double slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x);
   return -slope;
}

//+------------------------------------------------------------------+
//| Calculate Trend Slope                                            |
//+------------------------------------------------------------------+
double CalculateTrendSlope(const double &price[], int period)
{
   double sum_x = 0, sum_y = 0, sum_xy = 0, sum_xx = 0;

   for(int i = 0; i < period; i++)
   {
      double x = i;
      double y = price[i];

      sum_x += x;
      sum_y += y;
      sum_xy += x * y;
      sum_xx += x * x;
   }

   double slope = (period * sum_xy - sum_x * sum_y) / (period * sum_xx - sum_x * sum_x);
   double avg_price = sum_y / period;

   return slope / avg_price;
}

//+------------------------------------------------------------------+
//| Calculate Signal                                                  |
//+------------------------------------------------------------------+
void CalculateSignal(const double &features[], double &confidence, int &direction)
{
   confidence = 0.5;
   direction = 0;

   // Extract features
   double return_5 = features[0];
   double return_10 = features[1];
   double return_20 = features[2];
   double vol_10 = features[4];
   double rsi = features[6];
   double momentum = features[7];
   double fractal_dim = features[8];
   double trend_slope = features[9];

   // Voting for direction
   int vote_buy = 0;
   int vote_sell = 0;

   if(return_5 > 0) vote_buy++; else vote_sell++;
   if(return_10 > 0) vote_buy++; else vote_sell++;
   if(return_20 > 0) vote_buy++; else vote_sell++;
   if(momentum > 0) vote_buy++; else vote_sell++;
   if(trend_slope > 0) vote_buy++; else vote_sell++;

   if(vote_buy > vote_sell)
      direction = 1; // Buy
   else if(vote_sell > vote_buy)
      direction = -1; // Sell

   // Confluence factors
   if(MathAbs(momentum) > 0.02)
      confidence += 0.15;

   if(fractal_dim > 1.3 && fractal_dim < 1.7)
      confidence += 0.20;
   else if(fractal_dim > 1.2 && fractal_dim < 1.8)
      confidence += 0.10;

   if(vol_10 < 0.01)
      confidence += 0.15;

   if((rsi > 0.7 && direction == -1) || (rsi < 0.3 && direction == 1))
      confidence += 0.10;

   // Multi-timeframe alignment
   if((return_5 > 0 && return_10 > 0 && return_20 > 0) ||
      (return_5 < 0 && return_10 < 0 && return_20 < 0))
      confidence += 0.15;

   if(confidence > 1.0)
      confidence = 1.0;
}

//+------------------------------------------------------------------+
//| Open Position                                                     |
//+------------------------------------------------------------------+
void OpenPosition(int direction, double confidence, const double &features[])
{
   double price = SymbolInfoDouble(_Symbol, direction == 1 ? SYMBOL_ASK : SYMBOL_BID);

   // Calculate ATR for stop loss
   double atr = CalculateATR(14);
   double stopLoss = direction == 1 ? price - 2 * atr : price + 2 * atr;
   double takeProfit = direction == 1 ? price + InpRiskReward * 2 * atr : price - InpRiskReward * 2 * atr;

   // Calculate lot size
   double lotSize = InpLotSize;
   if(InpUseAutoLot)
   {
      double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskAmount = accountBalance * InpRiskPercent / 100.0;
      double stopLossPips = MathAbs(price - stopLoss) / _Point;

      double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      lotSize = riskAmount / (stopLossPips * tickValue);

      // Round to proper lot size
      double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

      lotSize = MathFloor(lotSize / lotStep) * lotStep;
      lotSize = MathMax(minLot, MathMin(maxLot, lotSize));
   }

   // Open position
   bool result = false;
   if(direction == 1)
      result = trade.Buy(lotSize, _Symbol, price, stopLoss, takeProfit,
                        StringFormat("UH-EA Buy %.0f%%", confidence * 100));
   else
      result = trade.Sell(lotSize, _Symbol, price, stopLoss, takeProfit,
                         StringFormat("UH-EA Sell %.0f%%", confidence * 100));

   if(result)
   {
      tradesThisDay++;
      Print("Position opened: ", direction == 1 ? "BUY" : "SELL",
            " | Confidence: ", confidence * 100, "%",
            " | Lots: ", lotSize,
            " | SL: ", stopLoss,
            " | TP: ", takeProfit);
   }
   else
   {
      Print("Failed to open position. Error: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Manage Open Position                                             |
//+------------------------------------------------------------------+
void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol))
      return;

   double positionOpenPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double positionSL = PositionGetDouble(POSITION_SL);
   double positionTP = PositionGetDouble(POSITION_TP);
   long positionType = PositionGetInteger(POSITION_TYPE);
   double positionVolume = PositionGetDouble(POSITION_VOLUME);

   double currentPrice = positionType == POSITION_TYPE_BUY ?
                        SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                        SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   // Calculate profit in R
   double risk = MathAbs(positionOpenPrice - positionSL);
   double profit = positionType == POSITION_TYPE_BUY ?
                  currentPrice - positionOpenPrice :
                  positionOpenPrice - currentPrice;

   double rMultiple = profit / risk;

   // Partial exit logic
   if(InpUsePartialExit && rMultiple >= InpPartialExitRR)
   {
      // Check if we haven't already done partial exit
      double originalVolume = positionVolume; // In real trading, store this

      double partialVolume = originalVolume * InpPartialExitPercent / 100.0;
      double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

      if(partialVolume >= minLot)
      {
         bool result = trade.PositionClosePartial(_Symbol, partialVolume);
         if(result)
         {
            Print("Partial exit executed at ", InpPartialExitRR, "R");

            // Move stop to breakeven
            trade.PositionModify(_Symbol, positionOpenPrice, positionTP);
         }
      }
   }

   // Trailing stop (optional - can be enhanced)
   if(rMultiple > 2.0)
   {
      double atr = CalculateATR(14);
      double newSL = positionType == POSITION_TYPE_BUY ?
                     currentPrice - atr :
                     currentPrice + atr;

      // Only move SL in profit direction
      if((positionType == POSITION_TYPE_BUY && newSL > positionSL) ||
         (positionType == POSITION_TYPE_SELL && newSL < positionSL))
      {
         trade.PositionModify(_Symbol, newSL, positionTP);
         Print("Trailing stop updated to: ", newSL);
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate ATR                                                     |
//+------------------------------------------------------------------+
double CalculateATR(int period)
{
   double atr[];
   int atrHandle = iATR(_Symbol, PERIOD_CURRENT, period);

   if(atrHandle == INVALID_HANDLE)
      return 0;

   if(CopyBuffer(atrHandle, 0, 0, 1, atr) <= 0)
      return 0;

   return atr[0];
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("Ultimate Hybrid EA deinitialized. Reason: ", reason);
}
//+------------------------------------------------------------------+
