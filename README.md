# fatigued_face_ml

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)


## 概要

本repositoryは、機械学習を用いて表情から疲労度を予測する疲労分析プロジェクトです。専用の[Androidアプリ](https://github.com/us2773/FatigueFaceCapture-Release-)で記録したデータを指定のディレクトリに格納しコマンドを実行することで、データセットの作成および機械学習を行うことができます。

本プロジェクトは大きく3つの段階に分かれます

1. **AU抽出**
    - OpenFaceを利用して顔動画からAU時系列データ（CSV）を抽出します。
2. **データセット作成**
    - 機械学習に用いるデータセットを作成します。
3. **機械学習**
    - SV回帰を用いた機械学習を行います。

本プロジェクトは分析のために以下が必要です。

- **顔動画**（.mp4他）
- **疲労度データ**（JSON）

本リポジトリには研究データは含まれていません。データは別途取得または生成する必要があります。いずれも専用Androidアプリで作成することができます。疲労度データはホーム画面の「開発者モード」をタップすることで、JSONファイルがエクスポートされます。ここには過去に記録した全ての動画に関する情報が保存されています。

```json
    {
        "dataID": 0,
        "userID": "user0",
        "movie_name": "yyyy-MM-dd-HH-mm-ss.mp4",
        "vas_sleepiness": 3,
        "vas_annoyed": 4,
        "vas_painful": 5,
        "date": "yyyyMMddHHmmss"
```

## クイックスタート

### 分析対象ファイルの用意

AU抽出から実行する場合は`data/01_raw/video`に顔動画を、`data/01_raw/json`に疲労度データを置きます。

データセット作成から行う場合は`data/01_raw/csv`にAU時系列データを、`data/01_raw/json`に疲労度データを置きます。置きます。

### 機械学習の実行方法

以下のコマンドでデータセットの生成及び機械学習を実行できます

```
kedro run
```

## 動作環境

本プロジェクトは以下の環境で動作確認を行っています。

- OS: Windows 11 (WSL2)
- Python: 3.12.0
- Docker Desktop
- Kedro 1.2.0

本プロジェクトでは以下の外部ソフトウェアを使用しています。

- OpenFace（表情解析ツールキット）

https://github.com/TadasBaltrusaitis/OpenFace

本研究で使用するAction UnitはOpenFaceにより抽出されています。抽出が必要となる際はOpenFaceを別途インストールしてください。

## Kedroについて

本プロジェクトは、データ分析および機械学習パイプライン管理フレームワークである[Kedro](https://kedro.org)を用いて構築されています。

ディレクトリ構成は Kedro テンプレートに基づいており、データ処理および機械学習処理は pipelineとnodeの概念に従って整理されています。

本リポジトリのディレクトリ構成は Kedro の公式テンプレートをベースとして生成されたものです。

- `src/` : パイプラインおよび処理ロジック
- `conf/` : 実行設定およびパラメータ
- `data/` : データ管理用ディレクトリ（Git管理外）
    - `01_raw`：生データ
        - 顔動画
        - JSONファイル
    - `02_intermediate`：途中生成物
        - OpenFaceで抽出したAU時系列データ
    - `03_primary`：クレンジング済データ
    - `04_feature`：特徴量生成済データ
    - `05_model_input`：モデルに直接渡すデータ
    - `06_models`：学習済モデル
    - `07_model_output`：予測結果
        - 予測結果をJSONで出力
    - `08_reporting`：成果物
        - スコア
        - データセット（preview）
- `pipelines`/ : データ処理・学習フロー定義

詳細については [Kedro 公式ドキュメント](https://docs.kedro.org)を参照してください。

### ルール及びガイドライン

本テンプレートを適切に利用するため、以下の点に注意してください。

- 提供されている `.gitignore`ファイルの内容を削除しないでください
- データエンジニアリングの慣習に従い、結果の再現性を確保してください
- データをリポジトリにコミットしないでください
- 認証情報やローカル設定をリポジトリにコミットしないでください。これらは`conf/local/`に保存してください

### Kedro プロジェクトのテスト方法

テストの書き方については`tests/test_run.py`を参照してください。
テストは以下のコマンドで実行できます。

```
pytest
```

### Kedro と Notebook の利用方法

> Note: 
`kedro jupyter`または `kedro ipython`を使用して `Notebook` を起動すると、`context`、`session`、`catalog`、`pipelines`の各変数があらかじめ利用可能になります。`Jupyter`、`JupyterLab`、および `IPython`はデフォルトで依存関係に含まれています。
`pip install -r requirements.txt`を実行すれば、追加の設定なしで利用できます。
> 

インストール後、以下でローカル Notebook サーバーを起動できます。

```
kedro jupyter notebook
```

## 導入

### 依存関係のインストール方法

pipによるインストールを行うため、必要なライブラリは`requirements.txt` に記述します。

インストールするには、以下を実行してください。

```
pip install -r requirements.txt
```

### OpenFace導入

注：AU時系列データは各々で生成せず全員で統一されたデータセットを利用する。よって基本的にOpenFaceの導入は不要。

AU抽出にはOpenFaceを使用する。環境構築にはDockerを使用します。DockerはLinux上でのみ動作するので、Windowsの場合は事前にWSLをインストールします。

#### Docker Desktopの導入

[公式サイト](https://www.docker.com/ja-jp/products/docker-desktop/)からDockerDesktopをインストールします。

次にDockerでopenfaceをインストールします。Powershellで以下のコマンドを実行してください。

```bash
docker run -it --rm algebr/openface:latest

```

Dockerデスクトップを開き、コンテナIDとコンテナ名を確認し、config.ps1に転記してください。

```powershell
$ContainerName = "your_openface_docker_container_name"
$ContainerID = "your_openface_docker_container_id"
```

## 実行

`kedro run` は作成したパイプラインを実行するコマンドです。Defaultで設定されたパイプライン（データセット作成→機械学習）が実行されます。それ以外のパイプラインを実行する際はオプションを指定します。

### AU抽出

AU抽出パイプラインを実行するには下記のコマンドを実行します。Dockerコンテナが立ち上がり、OpenFaceのコマンドが実行されます。

```
kedro run --pipeline feature_extraction
```
