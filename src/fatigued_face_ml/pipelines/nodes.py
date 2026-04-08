import pandas as pd
import os
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.signal import find_peaks, stft
import subprocess
from sklearn.model_selection import cross_val_score, LeaveOneOut
from sklearn.svm import SVR
from sklearn.preprocessing import MinMaxScaler
import glob 
from typing import Callable, Any
from datetime import datetime

inputdir = "data/01_raw/csv"
donedir = "done"
done_json_dir = f"{donedir}/json"
done_movie_dir = f"{donedir}/video"
jsondir = "json"
outputdir = "output"
resultdir =  "result"

au_map =["AU01", "AU02", "AU04", "AU05","AU06","AU07","AU09","AU10","AU12","AU14","AU15","AU17","AU20","AU23","AU25","AU26","AU45"]
au_map_int = [1,2,4,5,6,7,9,10,12,14,15,17,20,23,25,26,45]
AU_describe_list = ["Inner brow raiser", "Outer brow raiser",  "Brow lowerer",  "Upper lid raiser",  "Cheek raiser", "Lid tightener",   "Nose wrinkler", "Upper lip raiser", "Lip corner puller",  "Dimpler",  "Lip corner depressor",  "Chin raiser", "Lip stretcher",  "Lip tightener", "Lips part", "Lips part", "Blink"]

vas_list = ["vas_sleepiness", "vas_annoyed", "vas_painful"]

# OpenFace FeatureExtractionの実行(1 -> 2)
def run_OpenFace() -> dict:
    # PowerShell スクリプト実行
    ps_cmd = ["powershell", "-ExecutionPolicy", "ByPass", "-File", "Exec_FeatureExtraction.ps1"]
    result = subprocess.run(ps_cmd, text=True)
    print("PowerShell stdout:", result.stdout)
    print("PowerShell stderr:", result.stderr)
    
    return {
        "status": "completed",
        "timestamp": datetime.now().isoformat(),
        "returncode": result.returncode,
    }
    
def get_OpenFace_result() -> dict[pd.DataFrame]:
    # inputディレクトリの動画ファイルのリストを返す
    of_outputs = glob.glob(inputdir+"/*csv")
    movie_dict = {}
    for path in of_outputs:
        movie_name = os.path.splitext(os.path.basename(path))[0]

        # CSVを読み込みフレームワークが想定する形式で保存
        df = pd.read_csv(path, low_memory=False)

        movie_dict[movie_name] = df

    return movie_dict
    
# CSVをクレンジングしDataFrameを取得(2 -> 3)
def csv_to_dataframe(partitions: dict[str, Callable]) -> pd.DataFrame:
    dfs = []
    for name, load in partitions.items():
        df = load()
        df = df[(df[" success"] == 0) | (df[" success"] == 1)]
        movie_name = os.path.splitext(
            os.path.basename(name)
        )[0]
        df["movie_name"] = movie_name
        dfs.append(df)
        print(f"name:{name}")
    return pd.concat(dfs, ignore_index=True)
    
# 指定したAU時系列のトレンドとノイズを分離
def separate_AU_trend_noise(df: pd.DataFrame, plot_num: int) -> tuple[np.ndarray, np.ndarray] :
    AUR_start = df.columns.get_loc(" AU01_r")
    AUR_row = df.iloc[:, AUR_start + plot_num]
    AUR_name = df.columns[AUR_start + plot_num]
        
    # LOWESSによるトレンド抽出
    trend_est = lowess(AUR_row, df[" timestamp"], frac=0.1, return_sorted=False)
    # 残差計算
    residual = AUR_row - trend_est
    df[f"{AUR_name}_trend"] = trend_est
    df[f"{AUR_name}_fluct"] = residual
    return (trend_est, residual)

# 全てのAU時系列のトレンド平均・分散、ノイズ平均・分散を算出
def get_trend_noise(df: pd.DataFrame)-> dict:
    
    lst_AUR_moving_mean = []
    lst_AUR_moving_var = []
    lst_AUR_residual_mean = []
    lst_AUR_residual_var = []
    
    # AU種数分だけループ
    for plot_num in range(17) :
        trend_est, residual = separate_AU_trend_noise(df, plot_num)

        # 統計情報
        AUR_moving_mean = float(trend_est.mean())
        AUR_moving_var = float(trend_est.var())
        AUR_residual_mean = float(residual.mean())
        AUR_residual_var = float(residual.var())
        
        lst_AUR_moving_mean.append(AUR_moving_mean)
        lst_AUR_moving_var.append(AUR_moving_var)
        lst_AUR_residual_mean.append(AUR_residual_mean)
        lst_AUR_residual_var.append(AUR_residual_var)

    result_dict = {"AUR_moving_mean": lst_AUR_moving_mean, "AUR_moving_var": lst_AUR_moving_var,"AUR_residual_mean": lst_AUR_residual_mean, "AUR_residual_var": lst_AUR_residual_var}
    print(result_dict)
    return result_dict

# 指定したAU時系列のピーク点出現頻度の算出
def find_AU_peaks(df: pd.DataFrame, plot_num: int) -> tuple[list, list]:
    au_col = df.columns.get_loc(" AU01_r") + plot_num
    signal = df.iloc[:, au_col].values
    times = df[" timestamp"].values

    peaks, _ = find_peaks(signal, height=0.1, distance=5, prominence=0.1)
    return peaks, times

# 全てのAU時系列のピーク点出現回数・頻度を算出
def get_AU_peak(df: pd.DataFrame)-> dict[list, float]:
    lst_num = []
    lst_f = []
    for plot_num in range(17):
        peaks, times = find_AU_peaks(df, plot_num)

        num = len(peaks)
        print(num)
        if num == 0 :
            f = 0
        else :
            f = float(times[-1] / num)
        
        lst_num.append(num)
        lst_f.append(f)
        
    result_dict = {"num": lst_num, "freq": lst_f}
    return result_dict

# 指定したAU時系列の周波数成分の算出
def get_spectrums(df:pd.DataFrame, plot_num:int) -> tuple[float, float]:
    au_col = df.columns.get_loc(" AU01_r") + plot_num
    signal = df.iloc[:, au_col].values
        
    f, _, Zxx = stft(signal, fs=30, nperseg=20, noverlap=10)
    power  =np.abs(Zxx) ** 2
    
    mean_power = power.mean(axis=1)
    return f, mean_power

# 複数のJSONファイルを単一のmapにまとめる処理
def json_analyze(jsons: dict[str, Callable[[], Any]]) -> pd.DataFrame:

    records = []

    for _, load_json in jsons.items():
        json_list = load_json()

        for data in json_list:
            movie_name = os.path.splitext(os.path.basename( data["movie_name"]))[0]
            records.append({
                "movie_name":movie_name,
                "date": data["date"],
                "person": data["userID"],
                "vas_sleepiness": data["vas_sleepiness"],
                "vas_annoyed": data["vas_annoyed"],
                "vas_painful": data["vas_painful"],
            })

    meta_df = pd.DataFrame(records)
    print(meta_df["person"].head())
    return meta_df

# 特徴量生成済データの生成(3 -> 4)
def create_dataset(df_all: pd.DataFrame, meta_data:pd.DataFrame)-> pd.DataFrame :
    # カラム名の作成
    column_metadata = ["date", "person"]
    column_AUmean = [f"AU{x:02}_mean" for x in au_map_int]
    column_AUvar = [f"AU{x:02}_var" for x in au_map_int]
    column_AUpeakfreq = [f"AU{x:02}_peakfreq" for x in au_map_int]
    column_AUspectrum = []
    for x in au_map_int :
        for freq in [1.5, 3, 4.5, 6, 7.5, 9, 10.5, 12, 13.5, 15] :
            column_AUspectrum.append(f"AU{x:02}_spectrum_{freq}Hz")
    column_vas = ["vas_sleepiness","vas_annoyed","vas_painful"]
    columns = column_metadata + column_AUmean + column_AUvar + column_AUpeakfreq + column_AUspectrum +column_vas
    
    # 返り値の初期化
    df_dataset = pd.DataFrame(columns=columns)
    records = []

    # データセット作成
    for movie_name, df in df_all.groupby("movie_name"):
        
        meta_row = meta_data.loc[
            meta_data["movie_name"] == movie_name
        ]
        if meta_row.empty:
            raise ValueError(f"Metadata not found for {movie_name}")
        meta_row = meta_row.iloc[0]
            
        # 特徴量抽出
        result_trend_noise = get_trend_noise(df)
        result_peak = get_AU_peak(df)
        spectrums = []
        for i in au_map_int :
            _, mean_power = get_spectrums(df, i)
            mean_power = mean_power[1:]
            
            spectrums += list(mean_power)
        
        trend_mean = result_trend_noise["AUR_moving_mean"]
        trend_var = result_trend_noise["AUR_moving_var"]
        peak_freq = result_peak["freq"]
        
        
        # 特徴量をデータセットに追加
        fatigue_level = [meta_row["vas_sleepiness"], meta_row["vas_annoyed"], meta_row["vas_painful"]]
        record_list = [meta_row["date"], meta_row["person"]] + trend_mean + trend_var + peak_freq + spectrums + fatigue_level
        records.append(record_list)
        
    df_dataset = pd.DataFrame(records, columns=columns)
    return df_dataset

def preview_feature_dataset(df: pd.DataFrame) -> pd.DataFrame:
    return df

# 通常時との差分の計算
def get_diff_from_learningdata(df:pd.DataFrame, name:str, vas_num:int) :
    vas_list = ["vas_sleepiness", "vas_annoyed", "vas_painful"]
    fatigue_level = "fatigue_level"

    df_p1 = df[df["person"]==name].copy()
    min = df_p1[vas_list[vas_num]].min()
    # print(df_p1.head())
    # 総合疲労度カラムの追加
    df_p1[fatigue_level] = df_p1[vas_list[0]] + df_p1[vas_list[1]] + df_p1[vas_list[2]]
    # 指定した種類の主観疲労度が最も低いデータ行を抽出
    df_p1_vas_min = df_p1[df_p1[vas_list[vas_num]]==min]
    # print("df_p1_vas_min")
    # print(df_p1_vas_min)
    # 総合疲労度が低い順に並び替え
    df_p1_vas_min = df_p1_vas_min.sort_values(by=fatigue_level)
    # 総合疲労度が最も低い1データを基準に選出
    df_p1_vas_base = df_p1_vas_min.head(1)
    df_p1_vas_base.head()
    # print("df_p1_vas_base")
    # print(df_p1_vas_base)

    # 数値データ以外の列を除去
    df_p1 = df_p1.iloc[:, 3:-1]
    df_p1_vas_base = df_p1_vas_base.iloc[:, 3:-1]

    # 基準データフレームの作成
    # 差分演算用
    size = len(df_p1)
    df_p1_vas_base = pd.concat([df_p1_vas_base] * size).reset_index(drop=True)

    # インデックスのズレ修正
    df_p1 = df_p1.reset_index(drop=True)
    df_p1_vas_base = df_p1_vas_base.reset_index(drop=True)
    # 基準表情との差分データフレームを作成
    df_p1_diff = df_p1 - df_p1_vas_base
    # print(df_p1_diff.head())

    # print("return value")
    # print(f"return:{df_p1_vas_min[vas_list[vas_num]]}")

    return df_p1_diff, min

# 単一人物・単一疲労度の回帰分析
def learning_model (df: pd.DataFrame, vas_num:int, name, au_list:list[int])->SVR :
    model = SVR(kernel="rbf", C=1, epsilon=0.1, gamma='auto')
    
    # 全データ
    df_data = df[df["person"]==name]

    # print("訓練データを説明変数と目的変数に分割")
    x = df_data.iloc[:, au_list]
    # print(x_train.columns.values)
    # print(df_train_diff)
    y = df_data[vas_list[vas_num]]

    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    scaler_X.fit(x.values)
    scaler_y.fit(y.values.reshape(-1, 1))
    
    X_s = scaler_X.transform(x.values)
    y_s = scaler_y.transform(y.values.reshape(-1, 1)).ravel()


    # print("モデル適用")
    model.fit(X_s, y_s)
    
    return {
        "model": model,
        "scaler_X": scaler_X,
        "scaler_y": scaler_y,
    }

# 単一人物・単一疲労度の回帰分析のLOO交差検証
def leave_one_out_evaluate( df: pd.DataFrame, vas_num:int, name, au_list:list[int]) -> np.ndarray:
    model = SVR(kernel="rbf", C=1, epsilon=0.1, gamma='auto')

    loo = LeaveOneOut()

    diff_list = []
    # 訓練データのみから差分データ取得
    # 全データ
    df_data = df[df["person"]==name].copy()
    # print(df_data.columns.values)

    # スケーリング

    max = df_data.loc[:, "AU01_mean":"vas_painful"].max()
    min = df_data.loc[:, "AU01_mean":"vas_painful"].min()

    # 目的変数
    # print("目的変数")
    #df_target = df_data.loc[:,  vas_list[vas_num]]

    for train_index, test_index in loo.split(df_data):
        # 目的変数
        # print("目的変数")
        df_target = df_data.loc[:,  vas_list[vas_num]]

        # 訓練データの抽出
        # print("訓練データの抽出")
        train_data = df_data.iloc[train_index]
        # 訓練データから差分データ取得
        # print("訓練データから差分データ取得")
        df_train_diff, min_fatigue = get_diff_from_learningdata(train_data, name, vas_num)

        # print("訓練データを説明変数と目的変数に分割")
        x_train = df_train_diff.iloc[:, au_list]
        # print(x_train.columns.values)
        # print(df_train_diff)
        y_train = df_train_diff[vas_list[vas_num]]

        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        scaler_X.fit(x_train.values)
        scaler_y.fit(y_train.values.reshape(-1, 1))

        test = df_data.iloc[test_index]
        X_test = test.iloc[:, au_list].values
        X_test_s = scaler_X.transform(X_test)

        X_train_s = scaler_X.transform(x_train.values)
        y_train_s = scaler_y.transform(y_train.values.reshape(-1, 1)).ravel()

        X_train_df = pd.DataFrame(
        X_train_s,
        columns=x_train.columns
        )

        # print("モデル適用")
        model.fit(pd.DataFrame(X_train_df), y_train_s)

        y_pred_s = model.predict(pd.DataFrame(X_test_s))
        y_pred_diff_orig = scaler_y.inverse_transform(y_pred_s.reshape(-1, 1)).ravel()

        y_pred_diff_orig += min_fatigue

        print(y_pred_diff_orig)

        y_test = test.loc[:, vas_list[vas_num]].values
        print(y_test)

        diff = np.abs(y_test - y_pred_diff_orig) #MAE
        diff_list.append(diff)

    diff_arr = np.concatenate(diff_list)
    # print(f"name: {name}, vas_num: {vas_num}")
    MAE = diff_arr.mean()
    # print(f"MAE: {MAE}")
    
    return MAE
