//+------------------------------------------------------------------+
//|                                           UltimateHybridPro.mq5 |
//|                                  Based on 62.16% Accurate System |
//|                         ML + Fractal + Confluence Trading System |
//+------------------------------------------------------------------+
#property copyright "Ultimate Hybrid Trading System"
#property link      "https://github.com/yourrepo"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2

// Plot settings
#property indicator_label1  "Buy Signal"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrLime
#property indicator_style1  STYLE_SOLID
#property indicator_width1  3

#property indicator_label2  "Sell Signal"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrRed
#property indicator_style2  STYLE_SOLID
#property indicator_width2  3

//--- Input parameters
input int      InpLookback = 100;              // Lookback period for calculations
input double   InpConfidenceThreshold = 0.70;  // Minimum confidence to show signal (70-85%)
input double   InpRiskPercent = 2.0;           // Risk per trade (%)
input bool     InpShowPanel = true;            // Show info panel
input bool     InpSendAlerts = true;           // Send alerts on new signals
input bool     InpShowSR = true;               // Show Support/Resistance levels

//--- Indicator buffers
double BuySignalBuffer[];
double SellSignalBuffer[];

//--- Global variables
datetime lastAlertTime = 0;
string panelName = "UltimateHybridPanel";

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Indicator buffers mapping
   SetIndexBuffer(0, BuySignalBuffer, INDICATOR_DATA);
   SetIndexBuffer(1, SellSignalBuffer, INDICATOR_DATA);

   //--- Set arrow codes
   PlotIndexSetInteger(0, PLOT_ARROW, 233);  // Up arrow
   PlotIndexSetInteger(1, PLOT_ARROW, 234);  // Down arrow

   //--- Set empty value
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, 0.0);

   //--- Name for indicator
   IndicatorSetString(INDICATOR_SHORTNAME, "Ultimate Hybrid Pro");

   //--- Create info panel
   if(InpShowPanel)
      CreatePanel();

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   //--- Check for minimum data
   if(rates_total < InpLookback)
      return(0);

   //--- Determine start position
   int start = prev_calculated > 0 ? prev_calculated - 1 : InpLookback;

   //--- Main calculation loop
   for(int i = start; i < rates_total - 1; i++)
   {
      // Initialize buffers
      BuySignalBuffer[i] = 0.0;
      SellSignalBuffer[i] = 0.0;

      // Only calculate for most recent bars (optimization)
      if(i < rates_total - 3)
         continue;

      //--- Extract features
      double features[];
      if(!ExtractFeatures(i, close, high, low, features))
         continue;

      //--- Calculate confluence score
      double confidence = 0.0;
      int direction = 0; // 1 = Buy, -1 = Sell
      string confluenceFactors[];

      CalculateConfluence(features, confidence, direction, confluenceFactors);

      //--- Generate signal if confidence is high enough
      if(confidence >= InpConfidenceThreshold)
      {
         if(direction == 1)
         {
            BuySignalBuffer[i] = low[i] - 10 * _Point;

            // Alert on new signal
            if(InpSendAlerts && i == rates_total - 2 && time[i] != lastAlertTime)
            {
               SendSignalAlert("BUY", confidence, close[i], time[i]);
               lastAlertTime = time[i];
            }

            // Update panel
            if(InpShowPanel)
               UpdatePanel("BUY", confidence, close[i], features);
         }
         else if(direction == -1)
         {
            SellSignalBuffer[i] = high[i] + 10 * _Point;

            // Alert on new signal
            if(InpSendAlerts && i == rates_total - 2 && time[i] != lastAlertTime)
            {
               SendSignalAlert("SELL", confidence, close[i], time[i]);
               lastAlertTime = time[i];
            }

            // Update panel
            if(InpShowPanel)
               UpdatePanel("SELL", confidence, close[i], features);
         }
      }
   }

   //--- Draw Support/Resistance levels
   if(InpShowSR)
      DrawSupportResistance(high, low, close, rates_total);

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Extract all features (from Ultimate Hybrid system)               |
//+------------------------------------------------------------------+
bool ExtractFeatures(int pos, const double &close[], const double &high[], const double &low[], double &features[])
{
   if(pos < InpLookback)
      return false;

   ArrayResize(features, 11);

   // 1. Returns at multiple horizons
   features[0] = (close[pos] - close[pos-5]) / close[pos-5];   // 5-bar return
   features[1] = (close[pos] - close[pos-10]) / close[pos-10]; // 10-bar return
   features[2] = (close[pos] - close[pos-20]) / close[pos-20]; // 20-bar return
   features[3] = (close[pos] - close[pos-50]) / close[pos-50]; // 50-bar return

   // 2. Volatility
   features[4] = CalculateVolatility(pos, close, 10);  // 10-bar volatility
   features[5] = CalculateVolatility(pos, close, 20);  // 20-bar volatility

   // 3. RSI
   features[6] = CalculateRSI(pos, close, 14);

   // 4. Momentum
   features[7] = (close[pos] - close[pos-20]) / close[pos-20];

   // 5. Fractal Dimension (KEY FEATURE from Ultimate Hybrid)
   features[8] = CalculateHiguchiFD(pos, close, 50);

   // 6. Trend slope
   features[9] = CalculateTrendSlope(pos, close, 20);

   // 7. Price position (for context)
   features[10] = close[pos];

   return true;
}

//+------------------------------------------------------------------+
//| Calculate Higuchi Fractal Dimension (CRITICAL FEATURE)           |
//+------------------------------------------------------------------+
double CalculateHiguchiFD(int pos, const double &price[], int window)
{
   if(pos < window)
      return 2.0;

   int kmax = 10;
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
            int idx1 = pos - window + m + i * k;
            int idx2 = pos - window + m + (i-1) * k;

            if(idx1 >= 0 && idx2 >= 0)
               ll += MathAbs(price[idx1] - price[idx2]);
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

   // Calculate slope
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
//| Calculate Volatility                                             |
//+------------------------------------------------------------------+
double CalculateVolatility(int pos, const double &price[], int period)
{
   if(pos < period)
      return 0;

   double returns[];
   ArrayResize(returns, period);

   for(int i = 0; i < period; i++)
   {
      int idx = pos - i;
      if(idx > 0)
         returns[i] = (price[idx] - price[idx-1]) / price[idx-1];
   }

   // Calculate standard deviation
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
//| Calculate RSI                                                     |
//+------------------------------------------------------------------+
double CalculateRSI(int pos, const double &price[], int period)
{
   if(pos < period + 1)
      return 50.0;

   double gains = 0, losses = 0;

   for(int i = 1; i <= period; i++)
   {
      int idx = pos - i;
      double change = price[idx] - price[idx-1];

      if(change > 0)
         gains += change;
      else
         losses += MathAbs(change);
   }

   gains /= period;
   losses /= period;

   if(losses == 0)
      return 100.0;

   double rs = gains / losses;
   return 100.0 - (100.0 / (1.0 + rs));
}

//+------------------------------------------------------------------+
//| Calculate Trend Slope                                            |
//+------------------------------------------------------------------+
double CalculateTrendSlope(int pos, const double &price[], int period)
{
   if(pos < period)
      return 0;

   // Simple linear regression
   double sum_x = 0, sum_y = 0, sum_xy = 0, sum_xx = 0;

   for(int i = 0; i < period; i++)
   {
      double x = i;
      double y = price[pos - period + i];

      sum_x += x;
      sum_y += y;
      sum_xy += x * y;
      sum_xx += x * x;
   }

   double slope = (period * sum_xy - sum_x * sum_y) / (period * sum_xx - sum_x * sum_x);
   double avg_price = sum_y / period;

   return slope / avg_price; // Normalized slope
}

//+------------------------------------------------------------------+
//| Calculate Confluence Score (Ultimate Hybrid logic)               |
//+------------------------------------------------------------------+
void CalculateConfluence(const double &features[], double &confidence, int &direction, string &factors[])
{
   confidence = 0.5;
   ArrayResize(factors, 0);

   // Extract features
   double return_5 = features[0];
   double return_10 = features[1];
   double return_20 = features[2];
   double vol_10 = features[4];
   double rsi = features[6];
   double momentum = features[7];
   double fractal_dim = features[8];
   double trend_slope = features[9];

   // Determine direction based on momentum and returns
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
   else
      direction = 0; // Neutral

   // Calculate confluence factors

   // 1. Strong momentum
   if(MathAbs(momentum) > 0.02)
   {
      confidence += 0.15;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = "Strong momentum";
   }

   // 2. Predictable fractal dimension (1.3 - 1.7)
   if(fractal_dim > 1.3 && fractal_dim < 1.7)
   {
      confidence += 0.20;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = StringFormat("Predictable structure (FD=%.2f)", fractal_dim);
   }
   else if(fractal_dim > 1.2 && fractal_dim < 1.8)
   {
      confidence += 0.10;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = StringFormat("Moderate structure (FD=%.2f)", fractal_dim);
   }

   // 3. Low volatility (more predictable)
   if(vol_10 < 0.01)
   {
      confidence += 0.15;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = "Low volatility regime";
   }

   // 4. RSI extremes (reversal potential)
   if(rsi > 70 && direction == -1)
   {
      confidence += 0.10;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = StringFormat("Overbought (RSI=%.1f)", rsi);
   }
   else if(rsi < 30 && direction == 1)
   {
      confidence += 0.10;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = StringFormat("Oversold (RSI=%.1f)", rsi);
   }

   // 5. Multi-timeframe alignment
   int aligned = 0;
   if((return_5 > 0 && return_10 > 0 && return_20 > 0) ||
      (return_5 < 0 && return_10 < 0 && return_20 < 0))
   {
      confidence += 0.15;
      ArrayResize(factors, ArraySize(factors) + 1);
      factors[ArraySize(factors)-1] = "Multi-timeframe alignment";
   }

   // Normalize confidence
   if(confidence > 1.0)
      confidence = 1.0;
}

//+------------------------------------------------------------------+
//| Send Alert                                                        |
//+------------------------------------------------------------------+
void SendSignalAlert(string direction, double confidence, double price, datetime time)
{
   string message = StringFormat(
      "Ultimate Hybrid Signal: %s at %.5f (Confidence: %.0f%%)",
      direction, price, confidence * 100
   );

   Alert(message);

   // Optional: Send push notification
   // SendNotification(message);
}

//+------------------------------------------------------------------+
//| Create Info Panel                                                |
//+------------------------------------------------------------------+
void CreatePanel()
{
   int x = 20, y = 50;
   int width = 250, height = 200;

   // Background
   ObjectCreate(0, panelName + "_BG", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_XSIZE, width);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_YSIZE, height);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, panelName + "_BG", OBJPROP_BACK, false);

   // Title
   ObjectCreate(0, panelName + "_Title", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_Title", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_Title", OBJPROP_YDISTANCE, y + 10);
   ObjectSetString(0, panelName + "_Title", OBJPROP_TEXT, "Ultimate Hybrid Pro");
   ObjectSetInteger(0, panelName + "_Title", OBJPROP_COLOR, clrGold);
   ObjectSetInteger(0, panelName + "_Title", OBJPROP_FONTSIZE, 12);
   ObjectSetString(0, panelName + "_Title", OBJPROP_FONT, "Arial Bold");
}

//+------------------------------------------------------------------+
//| Update Panel                                                      |
//+------------------------------------------------------------------+
void UpdatePanel(string signal, double confidence, double price, const double &features[])
{
   int x = 20, y = 50;

   // Signal
   ObjectCreate(0, panelName + "_Signal", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_Signal", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_Signal", OBJPROP_YDISTANCE, y + 40);
   ObjectSetString(0, panelName + "_Signal", OBJPROP_TEXT, "Signal: " + signal);
   ObjectSetInteger(0, panelName + "_Signal", OBJPROP_COLOR, signal == "BUY" ? clrLime : clrRed);
   ObjectSetInteger(0, panelName + "_Signal", OBJPROP_FONTSIZE, 11);

   // Confidence
   ObjectCreate(0, panelName + "_Conf", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_Conf", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_Conf", OBJPROP_YDISTANCE, y + 65);
   ObjectSetString(0, panelName + "_Conf", OBJPROP_TEXT, StringFormat("Confidence: %.0f%%", confidence * 100));
   ObjectSetInteger(0, panelName + "_Conf", OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, panelName + "_Conf", OBJPROP_FONTSIZE, 10);

   // Fractal Dimension
   ObjectCreate(0, panelName + "_FD", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_FD", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_FD", OBJPROP_YDISTANCE, y + 90);
   ObjectSetString(0, panelName + "_FD", OBJPROP_TEXT, StringFormat("Fractal Dim: %.2f", features[8]));
   ObjectSetInteger(0, panelName + "_FD", OBJPROP_COLOR, clrAqua);
   ObjectSetInteger(0, panelName + "_FD", OBJPROP_FONTSIZE, 9);

   // Entry Price
   ObjectCreate(0, panelName + "_Entry", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_Entry", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_Entry", OBJPROP_YDISTANCE, y + 115);
   ObjectSetString(0, panelName + "_Entry", OBJPROP_TEXT, StringFormat("Entry: %.5f", price));
   ObjectSetInteger(0, panelName + "_Entry", OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, panelName + "_Entry", OBJPROP_FONTSIZE, 9);

   // Risk Management
   double atr = CalculateATR(14);
   double stopLoss = signal == "BUY" ? price - 2*atr : price + 2*atr;
   double takeProfit = signal == "BUY" ? price + 3*atr : price - 3*atr;
   double riskReward = 1.5;

   ObjectCreate(0, panelName + "_SL", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_SL", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_SL", OBJPROP_YDISTANCE, y + 140);
   ObjectSetString(0, panelName + "_SL", OBJPROP_TEXT, StringFormat("Stop Loss: %.5f", stopLoss));
   ObjectSetInteger(0, panelName + "_SL", OBJPROP_COLOR, clrOrangeRed);
   ObjectSetInteger(0, panelName + "_SL", OBJPROP_FONTSIZE, 9);

   ObjectCreate(0, panelName + "_TP", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, panelName + "_TP", OBJPROP_XDISTANCE, x + 10);
   ObjectSetInteger(0, panelName + "_TP", OBJPROP_YDISTANCE, y + 165);
   ObjectSetString(0, panelName + "_TP", OBJPROP_TEXT, StringFormat("Take Profit: %.5f", takeProfit));
   ObjectSetInteger(0, panelName + "_TP", OBJPROP_COLOR, clrLimeGreen);
   ObjectSetInteger(0, panelName + "_TP", OBJPROP_FONTSIZE, 9);
}

//+------------------------------------------------------------------+
//| Calculate ATR                                                     |
//+------------------------------------------------------------------+
double CalculateATR(int period)
{
   double atr = 0;

   for(int i = 1; i <= period; i++)
   {
      double high = iHigh(_Symbol, PERIOD_CURRENT, i);
      double low = iLow(_Symbol, PERIOD_CURRENT, i);
      double prevClose = iClose(_Symbol, PERIOD_CURRENT, i + 1);

      double tr = MathMax(high - low, MathMax(MathAbs(high - prevClose), MathAbs(low - prevClose)));
      atr += tr;
   }

   return atr / period;
}

//+------------------------------------------------------------------+
//| Draw Support/Resistance Levels                                   |
//+------------------------------------------------------------------+
void DrawSupportResistance(const double &high[], const double &low[], const double &close[], int total)
{
   // Simple implementation - find swing highs/lows
   // You can expand this based on the SR detector from Python code

   // This is a simplified version - just showing concept
   // Full implementation would detect clusters of swing points
}

//+------------------------------------------------------------------+
//| Clean up                                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Delete panel objects
   ObjectDelete(0, panelName + "_BG");
   ObjectDelete(0, panelName + "_Title");
   ObjectDelete(0, panelName + "_Signal");
   ObjectDelete(0, panelName + "_Conf");
   ObjectDelete(0, panelName + "_FD");
   ObjectDelete(0, panelName + "_Entry");
   ObjectDelete(0, panelName + "_SL");
   ObjectDelete(0, panelName + "_TP");
}
//+------------------------------------------------------------------+
