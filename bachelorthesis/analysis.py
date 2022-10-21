import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import yaml
from sklearn.cluster import KMeans


def single_trade_files_to_one():
    with open("collections.yaml", "r") as stream:
        collections = yaml.safe_load(stream)
    trades_list = []
    for collection in list(collections.keys()):
        path = collections[collection]["nft_trades_path"]
        if path != None:
            df = pd.read_csv("etherscan_csv_files/" + path)
            trades_list.append(df)
    return pd.concat(trades_list).drop("Unnamed: 0", axis=1)


def _keep_multiple_trades_nfts(df):
    df_formatted = df[
        (df.nft_id.isin(list(df[df.nft_id.duplicated(keep=False)].nft_id.unique())))
    ]
    return df_formatted


def format_trades_df(df):
    df_formatted = (
        df.drop("Unnamed: 0", axis=1)
        .reset_index(drop=True)
        .rename(columns={"Date Time (UTC)": "timestamp", "Txn Hash": "txn_hash"})
    )
    df_formatted["nft_id"] = (
        df_formatted["NFT"] + "_" + df_formatted["Token ID"].astype(str)
    )
    df_formatted["timestamp"] = pd.to_datetime(df_formatted["timestamp"], utc=True)
    df_formatted["Price"] = df_formatted["Price"].str.replace("WETH", "ETH")
    df_formatted["date"] = df_formatted["timestamp"].dt.date
    df_formatted = (
        df_formatted[
            (df_formatted["Market"] == "OpenSea")
            & (df_formatted["Action"] == "Bought")
            & (df_formatted["Type"] == 721)
            & (df_formatted["Price"] != "0 ETH ")
            & (df_formatted.Price.str.contains("$"))
            & (df_formatted["Price"].str.contains("ETH"))
        ]
        .pipe(_keep_multiple_trades_nfts)
        .drop_duplicates(subset=["timestamp", "nft_id"], keep="first")
        .drop_duplicates(subset=["txn_hash", "nft_id"], keep="first")
    )
    df_formatted["price_usd"] = (
        df_formatted["Price"]
        .apply(lambda st: st[st.find("($") + 2 : st.find(")")])
        .str.replace(",", "")
        .astype(float)
    )
    df_formatted["price_eth"] = (
        df_formatted["Price"]
        .str.split()
        .apply(lambda x: x[0])
        .str.replace(",", "")
        .astype(float)
    )
    df_formatted = (
        df_formatted[(df_formatted.price_eth < 1000) & (df_formatted.price_usd > 0)]
        .pipe(_keep_multiple_trades_nfts)
        .sort_values(["nft_id", "timestamp"])
        .reset_index(drop=True)
        .drop("UnixTimestamp", axis=1)
    )
    return df_formatted[
        ["date", "nft_id", "price_eth", "price_usd", "NFT", "Buyer", "txn_hash"]
    ]


def load_trades():
    return (
        pd.read_csv("historic_data/trades.csv", low_memory=False)
        .pipe(format_trades_df)
        .rename(columns={"NFT": "collection"})
    )


def load_nft_trades():
    nft_trades = pd.read_csv("historic_data/profits.csv", low_memory=False).set_index(
        ["nft_id", "trade_no"]
    )
    nft_trades["holding_period"] = pd.to_timedelta(nft_trades["holding_period"]).dt.days
    nft_trades["sell_date"] = pd.to_datetime(nft_trades["sell_date"])
    nft_trades["purchase_date"] = pd.to_datetime(nft_trades["purchase_date"])
    return nft_trades


def plot_total_nft_volume(nft_trades):
    return (
        nft_trades[["date", "price_usd"]]
        .rename(columns={"price_usd": "USD"})
        .groupby("date")
        .sum()
        .plot(grid=True, logy=True, title="Total NFT volume per [log values]")
    )


def get_trade_count(nft_trades):
    nft_trades["trade_count"] = None
    nft_list = nft_trades["nft_id"].tolist()
    i = 0
    for nft in nft_list:
        nft_counter = 0
        try:
            while nft == nft_list[i]:
                nft_counter += 1
                nft_trades.loc[i, "trade_count"] = nft_counter
                i += 1
        except:
            break
    return nft_trades.set_index(["nft_id", "trade_count"])


def calculate_profits(nft_trades):
    nft_profits = nft_trades.reset_index()

    nft_profits["profit_eth"] = None
    nft_profits["profit_usd"] = None
    nft_profits["purchase_price_eth"] = nft_profits["price_eth"].shift()
    nft_profits["purchase_price_usd"] = nft_profits["price_usd"].shift()
    nft_profits["purchase_date"] = nft_profits["date"].shift()
    nft_profits["sell_date"] = nft_profits["date"].copy()
    nft_profits["from_address"] = nft_profits["Buyer"].shift()
    nft_profits["to_address"] = nft_profits["Buyer"].copy()
    nft_profits["purchase_hash"] = nft_profits["txn_hash"].shift()
    nft_profits["sell_hash"] = nft_profits["txn_hash"].copy()

    nft_profits["holding_period"] = (
        nft_profits["sell_date"] - nft_profits["purchase_date"]
    )

    nft_profits["profit_eth"] = np.log(
        nft_profits["price_eth"] / nft_profits["price_eth"].shift()
    )
    nft_profits["profit_usd"] = np.log(
        nft_profits["price_usd"] / nft_profits["price_usd"].shift()
    )
    nft_profits["trade_count"] = nft_profits["trade_count"] - 1
    nft_profits = nft_profits.loc[nft_profits["trade_count"] != 0]
    nft_profits = nft_profits.rename(
        columns={
            "price_usd": "sell_price_usd",
            "price_eth": "sell_price_eth",
            "NFT": "collection",
            "trade_count": "trade_no",
        }
    )
    return nft_profits.set_index(["nft_id", "trade_no"])[
        [
            "purchase_date",
            "sell_date",
            "holding_period",
            "purchase_price_eth",
            "sell_price_eth",
            "profit_eth",
            "purchase_price_usd",
            "sell_price_usd",
            "profit_usd",
            "collection",
            "from_address",
            "to_address",
            "purchase_hash",
            "sell_hash",
        ]
    ]


def get_top_collections(nft_trades, n=5):
    top_collections = (
        nft_trades[["collection", "sell_price_usd"]]
        .groupby("collection")
        .sum()
        .sort_values("sell_price_usd", ascending=False)
        .head(n)
        .astype(int)
    )
    top_collections.sell_price_usd = top_collections.sell_price_usd.apply(
        lambda x: "${:,}".format(x)
    )
    return top_collections


def get_top_buyer(nft_trades, n=5):
    return (
        nft_trades[["to_address", "sell_price_usd"]]
        .groupby("to_address")
        .count()
        .sort_values("sell_price_usd", ascending=False)
        .head(n)
        .astype(int)
        .rename(columns={"sell_price_usd": "trade_count"})
    )


def limit_df(nft_trades, min_eth, max_eth, currency):
    return nft_trades[
        (nft_trades["purchase_price_" + currency] < max_eth)
        & (nft_trades["purchase_price_" + currency] > min_eth)
    ].reset_index()[["purchase_price_" + currency, "profit_" + currency]]


def cluster_kmeans(nft_trades_limited):
    y_pred = KMeans(5, n_init=100, max_iter=1000, algorithm="elkan")
    y_pred.fit(nft_trades_limited)
    return y_pred


def plot_limited(nft_trades_limited, min_eth, max_eth, currency, ax):
    subplot = nft_trades_limited.plot.scatter(
        x=("purchase_price_" + currency),
        y=("profit_" + currency),
        xlabel=currency.upper(),
        rot=("horizontal"),
        c="K-Means Profit Cluster",
        ylabel="Log-Returns*",
        marker=".",
        title="Purchase Price Range "
        + str(min_eth)
        + " - "
        + str(max_eth)
        + " "
        + currency.upper(),
        ax=ax,
        logy=True,
    )

    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

    ax.axhline(y=0, color="red", alpha=0.5, label="Log-Return: 0.0%", linestyle="--")
    ax.axhline(
        y=nft_trades_limited["profit_" + currency].mean(),
        color="green",
        alpha=1,
        label="Mean: "
        + str(round(nft_trades_limited["profit_" + currency].mean() * 100, 1))
        + "%",
    )
    ax.axhline(
        y=nft_trades_limited["profit_" + currency].median(),
        color="black",
        alpha=1,
        label="Median: "
        + str(round(nft_trades_limited["profit_" + currency].median() * 100, 1))
        + "%",
    )
    ax.legend(loc="upper right")
    ax.grid()


def get_return_per_eth(nft_trades, min_eth, max_eth, ax, currency="usd"):
    nft_trades_limited = limit_df(nft_trades, min_eth, max_eth, currency)
    y_pred = cluster_kmeans(nft_trades_limited)
    nft_trades_limited["K-Means Profit Cluster"] = y_pred.labels_.astype(float)
    plot_limited(nft_trades_limited, min_eth, max_eth, currency, ax)


def plot_figure_profit_per_price(splits, currency, nft_trades):
    a = 0
    i = 1
    fig, axes = plt.subplots(nrows=len(splits), ncols=1, figsize=(12, 16))
    axes = axes.ravel()
    cols = splits

    for col, eth_max, ax in zip(cols, splits, axes):
        get_return_per_eth(nft_trades, a, eth_max, ax, currency)
        a = eth_max
        i += 1
    ax.annotate(
        f"\n \n *Log-Returns calculated for NFT prices measured in {currency}",
        xy=(1.0, -0.2),
        xycoords="axes fraction",
        ha="right",
        va="center",
    )

    fig.tight_layout()
    plt.savefig(f"figures/nft_trades_{currency}.png")
    plt.show()


def collections_to_latex(nft_trades):
    collections = nft_trades.collection.unique()
    df = pd.DataFrame({1: collections[:45], 2: collections[44:]})
    df[2] = df[2].shift(-1)
    return df.to_latex()


def plot_correl_heatmap(correl_matrix):
    sns.heatmap(correl_matrix, annot=True, vmin=-1, vmax=1)
    plt.savefig("figures/correl.png")
    plt.show()


def plot_count_trades_per_day(nft_trades):
    nft_trades["sell_date"] = pd.to_datetime(nft_trades["sell_date"])

    plot_df = (
        nft_trades[["sell_date", "profit_usd"]]
        .groupby("sell_date")
        .count()
        .rename(columns={"profit_usd": "Count of Trades"})
        .loc["2019-01-01":]
        .reset_index()
    )

    ax = plot_df.plot.line(
        x="sell_date",
        y="Count of Trades",
        # c="Cluster",
        color="black",
        grid=True,
        xlabel="",
        # marker=".",
        ylabel="",
        title="Count of Trades per Day",
    )
    ax.xaxis.set_major_locator(mdates.MonthLocator([3, 9]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("\n%b\n%Y"))
    ax.set_xticklabels(ax.xaxis.get_majorticklabels(), rotation=0)

    plt.savefig("figures/trades_per_day.png")
    plt.show()


def get_counts(nft_trades):
    print(
        f"Collections: {len(nft_trades.collection.unique())}, \n"
        f"Trades: {nft_trades.count()[0]}, \n"
        f"Unique NFTs: {len(nft_trades.reset_index().nft_id.unique())}"
    )
    
def outlier_aware_hist(data, lower=None, upper=None):
    if not lower or lower < data.min():
        lower = data.min()
        lower_outliers = False
    else:
        lower_outliers = True

    if not upper or upper > data.max():
        upper = data.max()
        upper_outliers = False
    else:
        upper_outliers = True

    n, bins, patches = plt.hist(data, range=(lower, upper), bins=50, color="black")

    if lower_outliers:
        n_lower_outliers = (data < lower).sum()
        patches[0].set_height(patches[0].get_height() + n_lower_outliers)
        patches[0].set_facecolor("c")
        patches[0].set_label(
            "Lower outliers: ({:.2f}, {:.2f})".format(data.min(), lower)
        )

    if upper_outliers:
        n_upper_outliers = (data > upper).sum()
        patches[-1].set_height(patches[-1].get_height() + n_upper_outliers)
        patches[-1].set_facecolor("m")
        patches[-1].set_label(
            f"Outliers: Profit larger than {upper*100}%"
        )

    if lower_outliers or upper_outliers:
        plt.legend()
    plt.grid()
    plt.savefig("figures/returns_hist.png")