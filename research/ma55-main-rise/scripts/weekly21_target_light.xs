// 策略：週21MA活動靶3盤突破買點 + 主力籌碼開關（輕量版：先判日線，成立才算週線）
// 日線買點：前3日窄幅3盤，今日收紅過3盤高、量大於前日5/13/34均量、站上日55MA（前10日內曾貼近或跌破55MA）
// 週線背景：快漲 -> 整理2~10週 -> 回測週EMA21 -> 凹洞量 -> 整理期不破週55MA
// 主力開關：useMain=1 時，要求近 mainDays 日主力買賣超張數累計 > mainMin
Input: useMain(0, "主力濾網 1=開 0=關"), mainDays(5, "主力累計天數"), mainMin(0, "主力累計買賣超下限(張)");
Input: minGain(30, "旗桿漲幅下限%"), touchPct(12, "回測週EMA21容許%"), holeRatio(0.5, "凹洞量比例");
Input: narrowBar(11, "3盤單日振幅上限%"), narrowBox(14, "3盤箱體上限%"), minVol(500, "成交量下限(張)");
SetTotalBar(500);                                          // 80週約需400根日K
Var: i(0), j(0), k(0), hOff(0), lOff(0), hiV(0), loV(0), gainV(0);
Var: faceLow(0), faceVolMin(0), polVolMax(0), sumW(0), smaW(0);
Var: ctxOk(false), touchOk(false), aboveOk(false), trigOk(false);
Var: narrowOk(false), boxOk(false), volOk(false), touch55(false);
Var: boxHi(0), boxLo(0), maDay55(0), mainV(0), mainSum(0), volSum(0), mainPct(0);
Array: wkC[80](0), wkH[80](0), wkL[80](0), wkV[80](0), wkEma[80](0);

// ---- 1) 日線觸發（運算量小，先判斷）----
trigOk = false;
narrowOk = true;
for i = 1 to 3 begin                                       // 前3日每根振幅
    if Low[i] <= 0 then narrowOk = false
    else if (High[i] - Low[i]) / Low[i] * 100 > narrowBar then narrowOk = false;
end;
boxHi = Highest(High, 3)[1];                               // 前3日最高
boxLo = Lowest(Low, 3)[1];                                 // 前3日最低
boxOk = false;
if boxLo > 0 then begin
    if (boxHi - boxLo) / boxLo * 100 <= narrowBox then boxOk = true;
end;
volOk = false;
if Volume > Average(Volume, 5)[1] and Volume > Average(Volume, 13)[1] and Volume > Average(Volume, 34)[1] then
    volOk = true;                                          // 帶量：大於前日 5/13/34 日均量
maDay55 = Average(Close, 55);                              // 日55MA
touch55 = false;
for i = 1 to 10 begin                                      // 前10日內曾貼近或跌破日55MA
    if Close[i] <= Average(Close, 55)[i] * 1.03 then touch55 = true;
end;
if narrowOk = true and boxOk = true and Close > Open and Close > boxHi and volOk = true and Close > maDay55 and touch55 = true and Volume >= minVol then
    trigOk = true;

// ---- 2) 週線背景：只有日線觸發成立的K棒才計算 ----
ctxOk = false;
gainV = 0;
if trigOk = true then begin
    for i = 0 to 79 begin                                  // [0]=本週未收完，[1]=上一個已收完的週
        wkC[i] = GetField("收盤價", "W")[i];
        wkH[i] = GetField("最高價", "W")[i];
        wkL[i] = GetField("最低價", "W")[i];
        wkV[i] = GetField("成交量", "W")[i];
    end;
    wkEma[79] = wkC[79];                                   // 週EMA21，由舊到新遞推
    for k = 1 to 79 begin
        i = 79 - k;
        wkEma[i] = wkEma[i + 1] + (wkC[i] - wkEma[i + 1]) * 2 / 22;
    end;
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
            faceLow = wkL[1];                              // 初值取第1週的低點(同理不用固定大數)
            faceVolMin = wkV[1];                               // 初值取第1週的量(不可用固定大數,否則週量超過該數時凹洞條件失真)
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

// ---- 3) 主力籌碼（「主力買賣超張數」字尾含張數，已驗證欄位）----
mainV = GetField("主力買賣超張數", "D");
mainSum = Summation(mainV, mainDays);                      // 近N日主力買賣超累計
volSum = Summation(Volume, mainDays);
if volSum <> 0 then mainPct = mainSum * 100 / volSum else mainPct = 0;   // 主力累計比例%

// ---- 4) 輸出 ----
if ctxOk = true and trigOk = true and (useMain = 0 or mainSum > mainMin) then begin
    Ret = 1;
    OutputField1(gainV, "旗桿漲幅%");
    OutputField2(mainSum, "主力累計買賣超(張)");
    OutputField3(mainPct, "主力累計比例%");
    OutputField4(maDay55, "日55MA");
end;
