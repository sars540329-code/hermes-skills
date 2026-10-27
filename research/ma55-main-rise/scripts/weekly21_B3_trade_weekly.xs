// 策略：週21MA活動靶3盤突破 + 寶塔線翻黑出場（週線版交易腳本，頻率請選「週」）
// 每根週K收完才判斷：成立 -> 下一週開盤進場；翻黑/停損/持有滿期 -> 下一週開盤出場（與回測時點一致）
// 進場：週背景(快漲 -> 整理2~10週 -> 回測週EMA21 -> 凹洞量 -> 整理期不破週55MA)
//       週買點(收紅、收盤過前3週高點、站上週55MA、週量>前週5週均量、5週均量上揚)
//       流動性：該週成交量/5 >= minVol 張（預設 5000 張）
// 出場：寶塔線翻黑（收盤向下穿越前3週最低價，且前一週尚未是黑）；或 週收盤 <= 成本 x (1 - 停損%)；或持有滿 maxHold 週
// 回測設定：進場價、出場價都設為「下期開盤價」
Input: minVol(5000, "週量/5下限(張)"), stopPct(10, "停損%(以週收盤判斷)"), maxHold(32, "最長持有週數");
Input: minGain(30, "旗桿漲幅下限%"), touchPct(12, "回測週EMA21容許%"), holeRatio(0.5, "凹洞量比例");
Input: narrowBar(25, "3盤單週振幅上限%"), narrowBox(35, "3盤箱體上限%");
SetTotalBar(150);
Var: i(0), j(0), k(0), hOff(0), lOff(0), hiV(0), loV(0), gainV(0);
Var: faceLow(0), faceVolMin(0), polVolMax(0), sumW(0), smaW(0), sum5(0), mv5Now(0), mv5Prev(0), sma55Now(0);
Var: trigOk(false), ctxOk(false), touchOk(false), aboveOk(false), narrowOk(false), boxOk(false);
Var: boxHi(0), boxLo(0), hi3(0), hi3p(0), lo3(0), lo3p(0), ptState(0), holdBars(0);
Array: wkO[80](0), wkC[80](0), wkH[80](0), wkL[80](0), wkV[80](0), wkEma[80](0);

// ---- 1) 寶塔線狀態：1=紅 2=黑，沿用前一根（照 XQ 內建寶塔線 _reversal=1 的 cross over/under 邏輯）----
if CurrentBar > 6 then begin
    hi3 = Highest(High, 3)[1];                             // 前3根最高
    hi3p = Highest(High, 3)[2];                            // 前一根當時的前3根最高
    lo3 = Lowest(Low, 3)[1];                               // 前3根最低
    lo3p = Lowest(Low, 3)[2];
    if Close > hi3 and Close[1] <= hi3p then
        ptState = 1
    else if Close < lo3 and Close[1] >= lo3p then
        ptState = 2
    else
        ptState = ptState[1];
end;

// ---- 2) 持有週數計數 ----
if Position > 0 then holdBars = holdBars + 1 else holdBars = 0;

// ---- 3) 出場：停損、翻黑、持有滿期（收完這根週K，下一根開盤出）----
if Position > 0 and Filled > 0 then begin
    if Close <= FilledAvgPrice * (1 - stopPct / 100) then SetPosition(0, Market)
    else if ptState = 2 and ptState[1] <> 2 then SetPosition(0, Market)
    else if holdBars >= maxHold then SetPosition(0, Market);
end;

// ---- 4) 進場：空手、資料夠長、流動性通過才算 ----
if Position = 0 and CurrentBar > 85 and Volume / 5 >= minVol then begin
    for i = 0 to 5 begin                                   // [0]=這根(剛收完的週K)
        wkO[i] = Open[i];
        wkC[i] = Close[i];
        wkH[i] = High[i];
        wkL[i] = Low[i];
        wkV[i] = Volume[i];
    end;
    trigOk = false;
    narrowOk = true;
    for i = 1 to 3 begin                                   // 前3週每根振幅
        if wkL[i] <= 0 then narrowOk = false
        else if (wkH[i] - wkL[i]) / wkL[i] * 100 > narrowBar then narrowOk = false;
    end;
    boxHi = MaxList(wkH[1], wkH[2], wkH[3]);               // 前3週最高
    boxLo = MinList(wkL[1], wkL[2], wkL[3]);               // 前3週最低
    boxOk = false;
    if boxLo > 0 then begin
        if (boxHi - boxLo) / boxLo * 100 <= narrowBox then boxOk = true;
    end;
    sum5 = 0;
    for j = 0 to 4 begin
        sum5 = sum5 + wkV[j];
    end;
    mv5Now = sum5 / 5;                                     // 這週的5週均量
    sum5 = 0;
    for j = 1 to 5 begin
        sum5 = sum5 + wkV[j];
    end;
    mv5Prev = sum5 / 5;                                    // 上週的5週均量
    if narrowOk = true and boxOk = true and wkC[0] > wkO[0] and wkC[0] > boxHi and mv5Now > mv5Prev and wkV[0] > mv5Prev then
        trigOk = true;

    ctxOk = false;
    if trigOk = true then begin
        for i = 6 to 79 begin                              // 週買點成立才讀完整80週
            wkC[i] = Close[i];
            wkH[i] = High[i];
            wkL[i] = Low[i];
            wkV[i] = Volume[i];
        end;
        sumW = 0;
        for j = 0 to 54 begin
            sumW = sumW + wkC[j];
        end;
        sma55Now = sumW / 55;                              // 這週的週55MA
        if wkC[0] > sma55Now then begin
            wkEma[79] = wkC[79];                           // 週EMA21，由舊到新遞推
            for k = 1 to 79 begin
                i = 79 - k;
                wkEma[i] = wkEma[i + 1] + (wkC[i] - wkEma[i + 1]) * 2 / 22;
            end;
            hiV = 0;
            hOff = 0;
            for i = 1 to 19 begin                          // 近19週最高點（同高取較早的一根）
                if wkH[i] >= hiV then begin
                    hiV = wkH[i];
                    hOff = i;
                end;
            end;
            if hOff >= 3 and hOff <= 11 then begin         // 高點後整理 2~10 週
                loV = 999999;
                lOff = 0;
                for i = hOff + 3 to hOff + 8 begin         // 旗桿起點：高點前 3~8 週內的最低點
                    if wkL[i] > 0 and wkL[i] <= loV then begin
                        loV = wkL[i];
                        lOff = i;
                    end;
                end;
                gainV = 0;
                if loV > 0 and loV < 999999 then gainV = (hiV - loV) / loV * 100;
                if gainV >= minGain then begin
                    faceLow = wkL[1];
                    faceVolMin = wkV[1];
                    touchOk = false;
                    aboveOk = true;
                    for i = 1 to hOff - 1 begin            // 整理期逐週檢查
                        if wkL[i] < faceLow then faceLow = wkL[i];
                        if wkV[i] < faceVolMin then faceVolMin = wkV[i];
                        if wkL[i] <= wkEma[i] * (1 + touchPct / 100) then touchOk = true;   // 回測週EMA21
                        sumW = 0;
                        for j = i to i + 54 begin
                            sumW = sumW + wkC[j];
                        end;
                        smaW = sumW / 55;                  // 該週的週55MA
                        if wkC[i] < smaW then aboveOk = false;
                    end;
                    polVolMax = 0;
                    for i = hOff to lOff - 1 begin         // 旗桿期間最大週量
                        if wkV[i] > polVolMax then polVolMax = wkV[i];
                    end;
                    if faceLow >= loV and touchOk = true and aboveOk = true and faceVolMin <= holeRatio * polVolMax then
                        ctxOk = true;                      // 凹洞量：整理期最小週量 <= 旗桿最大週量 x 比例
                end;
            end;
        end;
    end;
    if ctxOk = true then SetPosition(1, Market);           // 下一週開盤進場
end;
