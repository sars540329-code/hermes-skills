// 策略：週21MA活動靶3盤突破 + 寶塔線翻黑出場（B3：翻黑 或 日收盤跌破成本10%）— 交易腳本，日線
// 進場：每週第一個交易日，用「上週已收完的週K」判斷，成立則隔日開盤進場
//       週背景：快漲 -> 整理2~10週 -> 回測週EMA21 -> 凹洞量 -> 整理期不破週55MA
//       週買點：上週收紅、收盤過前3週高點(3盤突破)、站上週55MA、週量>前週5週均量、5週均量上揚
//       成交量門檻：前一交易日的5日均量 >= minVol 張（預設 10000 張）
// 出場：(1) 每週第一個交易日判斷上週是否寶塔線翻黑（週收盤向下穿越前3週最低價），隔日開盤出場
//       (2) 日收盤 <= 成本 x (1 - 停損%)，隔日開盤出場   (3) 持有滿 maxHold 個交易日
// 回測設定請把「進場價」「出場價」都設為下期開盤價
Input: minVol(10000, "5日均量下限(張)"), stopPct(10, "停損%"), maxHold(160, "最長持有交易日");
Input: minGain(30, "旗桿漲幅下限%"), touchPct(12, "回測週EMA21容許%"), holeRatio(0.5, "凹洞量比例");
Input: narrowBar(25, "3盤單週振幅上限%"), narrowBox(35, "3盤箱體上限%");
SetTotalBar(520);                                          // 80週約需400根日K
Var: i(0), j(0), k(0), hOff(0), lOff(0), hiV(0), loV(0), gainV(0);
Var: faceLow(0), faceVolMin(0), polVolMax(0), sumW(0), smaW(0), sum5(0), mv5Now(0), mv5Prev(0), sma55Now(0);
Var: newWeek(false), cheapOk(false), trigOk(false), ctxOk(false), touchOk(false), aboveOk(false);
Var: narrowOk(false), boxOk(false);
Var: boxHi(0), boxLo(0), low3Now(0), low3Prev(0), holdBars(0);
Array: wkO[80](0), wkC[80](0), wkH[80](0), wkL[80](0), wkV[80](0), wkEma[80](0);

// ---- 0) 是否為新的一週的第一個交易日（今天的星期幾比昨天小）----
newWeek = false;
if CurrentBar > 1 then begin
    if DayOfWeek(Date) < DayOfWeek(Date[1]) then newWeek = true;
end;

// ---- 1) 持有天數計數 ----
if Position > 0 then holdBars = holdBars + 1 else holdBars = 0;

// ---- 2) 日線出場：停損、持有滿期 ----
if Position > 0 and Filled > 0 then begin
    if Close <= FilledAvgPrice * (1 - stopPct / 100) then SetPosition(0, Market)
    else if holdBars >= maxHold then SetPosition(0, Market);
end;

// ---- 3) 每週第一個交易日才讀週線（有部位，或成交量門檻通過才讀，節省運算）----
cheapOk = false;
if newWeek = true then begin
    if Position > 0 then cheapOk = true
    else if Average(Volume, 5)[1] >= minVol and CurrentBar >= 430 then cheapOk = true;
end;

if cheapOk = true then begin
    for i = 0 to 5 begin                                   // 先讀最近6週：[0]=上週(已收完)，[1]=上上週...
        wkO[i] = GetField("開盤價", "W")[i + 1];
        wkC[i] = GetField("收盤價", "W")[i + 1];
        wkH[i] = GetField("最高價", "W")[i + 1];
        wkL[i] = GetField("最低價", "W")[i + 1];
        wkV[i] = GetField("成交量", "W")[i + 1];
    end;

    // ---- 3a) 寶塔線翻黑出場：上週收盤 < 前3週最低，且前一週尚未在其前3週最低之下 ----
    if Position > 0 then begin
        low3Now = MinList(wkL[1], wkL[2], wkL[3]);
        low3Prev = MinList(wkL[2], wkL[3], wkL[4]);
        if wkC[0] < low3Now and wkC[1] >= low3Prev then SetPosition(0, Market);
    end;

    // ---- 3b) 進場判斷（空手才找）----
    if Position = 0 then begin
        trigOk = false;
        narrowOk = true;
        for i = 1 to 3 begin                               // 前3週每根振幅
            if wkL[i] <= 0 then narrowOk = false
            else if (wkH[i] - wkL[i]) / wkL[i] * 100 > narrowBar then narrowOk = false;
        end;
        boxHi = MaxList(wkH[1], wkH[2], wkH[3]);           // 前3週最高
        boxLo = MinList(wkL[1], wkL[2], wkL[3]);           // 前3週最低
        boxOk = false;
        if boxLo > 0 then begin
            if (boxHi - boxLo) / boxLo * 100 <= narrowBox then boxOk = true;
        end;
        sum5 = 0;
        for j = 0 to 4 begin
            sum5 = sum5 + wkV[j];
        end;
        mv5Now = sum5 / 5;                                 // 上週的5週均量
        sum5 = 0;
        for j = 1 to 5 begin
            sum5 = sum5 + wkV[j];
        end;
        mv5Prev = sum5 / 5;                                // 上上週的5週均量
        if narrowOk = true and boxOk = true and wkC[0] > wkO[0] and wkC[0] > boxHi and mv5Now > mv5Prev and wkV[0] > mv5Prev then
            trigOk = true;

        ctxOk = false;
        if trigOk = true then begin
            for i = 6 to 79 begin                          // 週買點成立才讀完整80週
                wkC[i] = GetField("收盤價", "W")[i + 1];
                wkH[i] = GetField("最高價", "W")[i + 1];
                wkL[i] = GetField("最低價", "W")[i + 1];
                wkV[i] = GetField("成交量", "W")[i + 1];
            end;
            sumW = 0;
            for j = 0 to 54 begin
                sumW = sumW + wkC[j];
            end;
            sma55Now = sumW / 55;                          // 上週的週55MA
            if wkC[0] > sma55Now then begin
                wkEma[79] = wkC[79];                       // 週EMA21，由舊到新遞推
                for k = 1 to 79 begin
                    i = 79 - k;
                    wkEma[i] = wkEma[i + 1] + (wkC[i] - wkEma[i + 1]) * 2 / 22;
                end;
                hiV = 0;
                hOff = 0;
                for i = 1 to 19 begin                      // 近19週最高點（同高取較早的一根）
                    if wkH[i] >= hiV then begin
                        hiV = wkH[i];
                        hOff = i;
                    end;
                end;
                if hOff >= 3 and hOff <= 11 then begin     // 高點後整理 2~10 週
                    loV = 999999;
                    lOff = 0;
                    for i = hOff + 3 to hOff + 8 begin     // 旗桿起點：高點前 3~8 週內的最低點
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
                        for i = 1 to hOff - 1 begin        // 整理期逐週檢查
                            if wkL[i] < faceLow then faceLow = wkL[i];
                            if wkV[i] < faceVolMin then faceVolMin = wkV[i];
                            if wkL[i] <= wkEma[i] * (1 + touchPct / 100) then touchOk = true;
                            sumW = 0;
                            for j = i to i + 54 begin
                                sumW = sumW + wkC[j];
                            end;
                            smaW = sumW / 55;              // 該週的週55MA
                            if wkC[i] < smaW then aboveOk = false;
                        end;
                        polVolMax = 0;
                        for i = hOff to lOff - 1 begin     // 旗桿期間最大週量
                            if wkV[i] > polVolMax then polVolMax = wkV[i];
                        end;
                        if faceLow >= loV and touchOk = true and aboveOk = true and faceVolMin <= holeRatio * polVolMax then
                            ctxOk = true;                  // 凹洞量：整理期最小週量 <= 旗桿最大週量 x 比例
                    end;
                end;
            end;
        end;
        if ctxOk = true then SetPosition(1, Market);       // 隔日開盤進場
    end;
end;
