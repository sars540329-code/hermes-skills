// 策略：週21MA活動靶3盤突破 + 寶塔線翻黑出場（週線版選股腳本，頻率請選「週」）
// 模式切換：
//   selectMode = 1（預設）：選出「本週剛完成週21MA活動靶3盤突破」之買進起漲標的
//   selectMode = 2：選出「本週寶塔線剛翻黑（收盤跌破前3週低點）」之出場警示標的（用於庫存檢視）
//
// 買進條件（selectMode = 1）：
//   1. 流動性：本週成交量/5 >= minVol 張（預設 5000 張）
//   2. 買點：本週收紅、收盤突破前3週最高點(3盤)、站上週55MA、本週量 > 上週5週均量、5週均量上揚
//   3. 整理：前3週窄幅整理（單週振幅 <= narrowBar%、箱體 <= narrowBox%）
//   4. 背景：高點前 3~8 週快漲（旗桿漲幅 >= minGain%），高點後整理 2~10 週回測週EMA21（touchPct%內），
//            凹洞量（整理期最小週量 <= 旗桿最大量 x holeRatio），整理期收盤守住週55MA
//
// 出場條件（selectMode = 2）：
//   本週寶塔線剛翻黑（收盤向下穿越前3週最低價，且前一週尚未為黑）
Input: selectMode(1, "模式", inputkind:=Dict(["1.買進突破選股", 1], ["2.寶塔翻黑出場", 2]));
Input: minVol(5000, "週量/5下限(張)"), minGain(30, "旗桿漲幅下限%"), touchPct(12, "回測週EMA21容許%");
Input: holeRatio(0.5, "凹洞量比例"), narrowBar(25, "3盤單週振幅上限%"), narrowBox(35, "3盤箱體上限%");

SetTotalBar(150);

Var: i(0), j(0), k(0), hOff(0), lOff(0), hiV(0), loV(0), gainV(0);
Var: faceLow(0), faceVolMin(0), polVolMax(0), sumW(0), smaW(0), sum5(0), mv5Now(0), mv5Prev(0), sma55Now(0);
Var: trigOk(false), ctxOk(false), touchOk(false), aboveOk(false), narrowOk(false), boxOk(false);
Var: boxHi(0), boxLo(0), hi3(0), hi3p(0), lo3(0), lo3p(0), ptState(0);
Array: wkO[80](0), wkC[80](0), wkH[80](0), wkL[80](0), wkV[80](0), wkEma[80](0);

// ==========================================
// 模式 2：寶塔線翻黑出場檢視
// ==========================================
if selectMode = 2 then begin
    if CurrentBar > 6 then begin
        hi3 = Highest(High, 3)[1];
        hi3p = Highest(High, 3)[2];
        lo3 = Lowest(Low, 3)[1];
        lo3p = Lowest(Low, 3)[2];
        if Close > hi3 and Close[1] <= hi3p then
            ptState = 1
        else if Close < lo3 and Close[1] >= lo3p then
            ptState = 2
        else
            ptState = ptState[1];

        // 本週剛翻黑
        if ptState = 2 and ptState[1] <> 2 then begin
            Ret = 1;
            OutputField1(Close, "本週收盤價");
            OutputField2(lo3, "前3週跌破點");
            OutputField3(Volume / 5, "週日均量(張)");
        end;
    end;
end;

// ==========================================
// 模式 1：週21MA活動靶3盤突破買進選股
// ==========================================
if selectMode = 1 then begin
    if CurrentBar > 85 and Volume / 5 >= minVol then begin
        for i = 0 to 5 begin
            wkO[i] = Open[i];
            wkC[i] = Close[i];
            wkH[i] = High[i];
            wkL[i] = Low[i];
            wkV[i] = Volume[i];
        end;

        trigOk = false;
        narrowOk = true;
        for i = 1 to 3 begin
            if wkL[i] <= 0 then narrowOk = false
            else if (wkH[i] - wkL[i]) / wkL[i] * 100 > narrowBar then narrowOk = false;
        end;

        boxHi = MaxList(wkH[1], wkH[2], wkH[3]);
        boxLo = MinList(wkL[1], wkL[2], wkL[3]);
        boxOk = false;
        if boxLo > 0 then begin
            if (boxHi - boxLo) / boxLo * 100 <= narrowBox then boxOk = true;
        end;

        sum5 = 0;
        for j = 0 to 4 begin
            sum5 = sum5 + wkV[j];
        end;
        mv5Now = sum5 / 5;

        sum5 = 0;
        for j = 1 to 5 begin
            sum5 = sum5 + wkV[j];
        end;
        mv5Prev = sum5 / 5;

        if narrowOk = true and boxOk = true and wkC[0] > wkO[0] and wkC[0] > boxHi and mv5Now > mv5Prev and wkV[0] > mv5Prev then
            trigOk = true;

        ctxOk = false;
        if trigOk = true then begin
            for i = 6 to 79 begin
                wkC[i] = Close[i];
                wkH[i] = High[i];
                wkL[i] = Low[i];
                wkV[i] = Volume[i];
            end;

            sumW = 0;
            for j = 0 to 54 begin
                sumW = sumW + wkC[j];
            end;
            sma55Now = sumW / 55;

            if wkC[0] > sma55Now then begin
                wkEma[79] = wkC[79];
                for k = 1 to 79 begin
                    i = 79 - k;
                    wkEma[i] = wkEma[i + 1] + (wkC[i] - wkEma[i + 1]) * 2 / 22;
                end;

                hiV = 0;
                hOff = 0;
                for i = 1 to 19 begin
                    if wkH[i] >= hiV then begin
                        hiV = wkH[i];
                        hOff = i;
                    end;
                end;

                if hOff >= 3 and hOff <= 11 then begin
                    loV = 999999;
                    lOff = 0;
                    for i = hOff + 3 to hOff + 8 begin
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
                        for i = 1 to hOff - 1 begin
                            if wkL[i] < faceLow then faceLow = wkL[i];
                            if wkV[i] < faceVolMin then faceVolMin = wkV[i];
                            if wkL[i] <= wkEma[i] * (1 + touchPct / 100) then touchOk = true;
                            sumW = 0;
                            for j = i to i + 54 begin
                                sumW = sumW + wkC[j];
                            end;
                            smaW = sumW / 55;
                            if wkC[i] < smaW then aboveOk = false;
                        end;

                        polVolMax = 0;
                        for i = hOff to lOff - 1 begin
                            if wkV[i] > polVolMax then polVolMax = wkV[i];
                        end;

                        if faceLow >= loV and touchOk = true and aboveOk = true and faceVolMin <= holeRatio * polVolMax then
                            ctxOk = true;
                    end;
                end;
            end;
        end;

        if ctxOk = true then begin
            Ret = 1;
            OutputField1(gainV, "旗桿漲幅%");
            OutputField2(hOff - 1, "整理週數");
            OutputField3(boxLo, "前3週低點(防守)");
            OutputField4(Volume / 5, "週日均量(張)");
        end;
    end;
end;