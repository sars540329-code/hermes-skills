// 策略：週線版 週21MA活動靶3盤突破（選股腳本，請用「週」頻率執行）
// 週線背景：快漲(旗桿) -> 整理2~10週(角度緩) -> 回測週EMA21 -> 凹洞量 -> 整理期不破週55MA
// 週線買點：本週收紅、收盤過前3週高點(3盤)、站上週55MA、週量>前週5週均量、5週均量上揚
// 主力開關：useMain=1 時，要求近 mainDays 週主力買賣超張數累計 > mainMin（日資料換算為週）
// 注意：本週未收完時，週K會隨盤中變動；要確認請在週五收盤後執行
Input: useMain(0, "主力濾網 1=開 0=關"), mainMin(0, "本週主力買賣超下限(張)");
Input: minGain(30, "旗桿漲幅下限%"), touchPct(12, "回測週EMA21容許%"), holeRatio(0.5, "凹洞量比例");
Input: narrowBar(25, "3盤單週振幅上限%"), narrowBox(35, "3盤箱體上限%"), minVol(1000, "本週成交量下限(張)");
SetTotalBar(500);                                          // 80週約需400根日K
Var: i(0), j(0), k(0), hOff(0), lOff(0), hiV(0), loV(0), gainV(0);
Var: faceLow(0), faceVolMin(0), polVolMax(0), sumW(0), smaW(0), sum5(0), mv5Now(0), mv5Prev(0);
Var: ctxOk(false), touchOk(false), aboveOk(false), trigOk(false), narrowOk(false), boxOk(false);
Var: boxHi(0), boxLo(0), sma55Now(0), mainSum(0), volWeek(0), mainPct(0);
Array: wkO[80](0), wkC[80](0), wkH[80](0), wkL[80](0), wkV[80](0), wkEma[80](0);

// ---- 1) 取週線資料：[0]=本週，[1]=上一個已收完的週 ----
for i = 0 to 79 begin
    wkO[i] = GetField("開盤價", "W")[i];
    wkC[i] = GetField("收盤價", "W")[i];
    wkH[i] = GetField("最高價", "W")[i];
    wkL[i] = GetField("最低價", "W")[i];
    wkV[i] = GetField("成交量", "W")[i];
end;
wkEma[79] = wkC[79];                                       // 週EMA21，由舊到新遞推
for k = 1 to 79 begin
    i = 79 - k;
    wkEma[i] = wkEma[i + 1] + (wkC[i] - wkEma[i + 1]) * 2 / 22;
end;

// ---- 2) 週線買點（先判斷，運算量小）----
trigOk = false;
narrowOk = true;
for i = 1 to 3 begin                                       // 前3週每根振幅
    if wkL[i] <= 0 then narrowOk = false
    else if (wkH[i] - wkL[i]) / wkL[i] * 100 > narrowBar then narrowOk = false;
end;
boxHi = MaxList(wkH[1], wkH[2], wkH[3]);                   // 前3週最高
boxLo = MinList(wkL[1], wkL[2], wkL[3]);                   // 前3週最低
boxOk = false;
if boxLo > 0 then begin
    if (boxHi - boxLo) / boxLo * 100 <= narrowBox then boxOk = true;
end;
sumW = 0;
for j = 0 to 54 begin
    sumW = sumW + wkC[j];
end;
sma55Now = sumW / 55;                                      // 本週的週55MA
sum5 = 0;
for j = 0 to 4 begin
    sum5 = sum5 + wkV[j];
end;
mv5Now = sum5 / 5;                                         // 本週的5週均量
sum5 = 0;
for j = 1 to 5 begin
    sum5 = sum5 + wkV[j];
end;
mv5Prev = sum5 / 5;                                        // 上週的5週均量
if narrowOk = true and boxOk = true and wkC[0] > wkO[0] and wkC[0] > boxHi and wkC[0] > sma55Now and mv5Now > mv5Prev and wkV[0] > mv5Prev and wkV[0] >= minVol then
    trigOk = true;

// ---- 3) 週線背景：只有買點成立才計算 ----
ctxOk = false;
gainV = 0;
if trigOk = true then begin
    hiV = 0;
    hOff = 0;
    for i = 1 to 19 begin                                  // 近19週最高點（同高取較早的一根）
        if wkH[i] >= hiV then begin
            hiV = wkH[i];
            hOff = i;
        end;
    end;
    if hOff >= 3 and hOff <= 11 then begin                 // 高點後整理 2~10 週
        loV = 999999;
        lOff = 0;
        for i = hOff + 3 to hOff + 8 begin                 // 旗桿起點：高點前 3~8 週內的最低點
            if wkL[i] > 0 and wkL[i] <= loV then begin
                loV = wkL[i];
                lOff = i;
            end;
        end;
        if loV > 0 and loV < 999999 then gainV = (hiV - loV) / loV * 100;
        if gainV >= minGain then begin
            faceLow = wkL[1];
            faceVolMin = wkV[1];
            touchOk = false;
            aboveOk = true;
            for i = 1 to hOff - 1 begin                    // 整理期逐週檢查
                if wkL[i] < faceLow then faceLow = wkL[i];
                if wkV[i] < faceVolMin then faceVolMin = wkV[i];
                if wkL[i] <= wkEma[i] * (1 + touchPct / 100) then touchOk = true;   // 回測週EMA21
                sumW = 0;
                for j = i to i + 54 begin
                    sumW = sumW + wkC[j];
                end;
                smaW = sumW / 55;                          // 該週的週55MA
                if wkC[i] < smaW then aboveOk = false;     // 整理期收盤不可跌破週55MA
            end;
            polVolMax = 0;
            for i = hOff to lOff - 1 begin                 // 旗桿期間最大週量
                if wkV[i] > polVolMax then polVolMax = wkV[i];
            end;
            if faceLow >= loV and touchOk = true and aboveOk = true and faceVolMin <= holeRatio * polVolMax then
                ctxOk = true;                              // 凹洞量：整理期最小週量 <= 旗桿最大週量 x 比例
        end;
    end;
end;

// ---- 4) 主力（本週）：用日資料累計本週主力買賣超 ----
volWeek = wkV[0];
mainSum = Summation(GetField("主力買賣超張數", "D"), 5);   // 近5個交易日主力買賣超累計
if volWeek <> 0 then mainPct = mainSum * 100 / volWeek else mainPct = 0;

// ---- 5) 輸出 ----
if ctxOk = true and trigOk = true and (useMain = 0 or mainSum > mainMin) then begin
    Ret = 1;
    OutputField1(gainV, "旗桿漲幅%");
    OutputField2(mainSum, "近5日主力買賣超(張)");
    OutputField3(mainPct, "主力佔本週量%");
    OutputField4(sma55Now, "週55MA");
end;
