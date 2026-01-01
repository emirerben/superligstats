import os
import ScraperFC as sfc  # LEAVE THIS!
import pandas as pd


def get_top_tacklers_super_lig(
    season: str = "25/26",
    top_n: int = 15,
    min_age: int | None = None,
    max_age: int | None = None,
) -> pd.DataFrame:
    """
    Get top tacklers in the Turkish Super Lig.

    Preferred path:
      - Load from local CSV (`tackles_joined.csv`) which you already generated.
    Fallback:
      - Use ScraperFC's Sofascore scraper (may fail if Sofascore API changes or blocks scraping,
        which is what causes the `KeyError: 'seasons'` you saw).
    """
    csv_path = "tackles_joined.csv"

    # --- Fast path: use local joined data if available ---
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)

        # Choose an age column if present
        age_col = None
        if "age" in df.columns:
            age_col = "age"
        elif "age_x" in df.columns:
            age_col = "age_x"
        elif "age_y" in df.columns:
            age_col = "age_y"

        # Optional age filtering
        if age_col is not None:
            if min_age is not None:
                df = df[(df[age_col] >= min_age) | (df[age_col].isna())]
            if max_age is not None:
                df = df[(df[age_col] <= max_age) | (df[age_col].isna())]

        # Sort & take top N
        df = df.dropna(subset=["tackles"])
        top = (
            df.sort_values("tackles", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

        # Normalise age column name
        if age_col is not None and age_col != "age":
            top = top.rename(columns={age_col: "age"})

        # Ensure position & nationality columns always exist, even if empty
        for col in ["position", "nationality"]:
            if col not in top.columns:
                top[col] = None

        return top[["player", "team", "age", "tackles", "position", "nationality"]]

    # --- Fallback: live scrape via ScraperFC / Sofascore ---
    ss = sfc.Sofascore()

    try:
        df = ss.scrape_player_league_stats(
            year=season,
            league="Turkish Super Lig",
            accumulation="total",
        )
    except KeyError as e:
        # This is the error you hit: the Sofascore endpoint stopped returning
        # a 'seasons' key, so ScraperFC blows up. Make the message explicit.
        raise RuntimeError(
            "ScraperFC failed while fetching seasons from Sofascore "
            "(missing 'seasons' key in API response). "
            "Either update ScraperFC / try again later, or create "
            "'tackles_joined.csv' and let this function load from it instead."
        ) from e

    df = df[["player", "team", "tackles", "position", "age"]].dropna(
        subset=["tackles"]
    )

    # Fetch extra player info
    player_info: list[dict] = []
    for player in df["player"].unique():
        try:
            info = ss.scrape_player_info(player)
            player_info.append(
                {
                    "player": player,
                    "age": info.get("age"),
                    "position": info.get("position"),
                    "nationality": info.get("nationality"),
                }
            )
        except Exception:
            # Player page not found or ambiguous name; skip
            continue

    player_info_df = pd.DataFrame(player_info)

    if not player_info_df.empty and "player" in player_info_df.columns:
        df = df.merge(player_info_df, on="player", how="left")
    else:
        df["age"] = None
        df["position"] = None
        df["nationality"] = None

    # Optional age filtering
    if min_age is not None:
        df = df[(df["age"] >= min_age) | (df["age"].isna())]
    if max_age is not None:
        df = df[(df["age"] <= max_age) | (df["age"].isna())]

    top = (
        df.sort_values("tackles", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return top[["player", "team", "age", "tackles", "position", "nationality"]]


if __name__ == "__main__":
    top_tacklers = get_top_tacklers_super_lig(
        season="25/26",
        top_n=15,
        min_age=None,
        max_age=None,
    )
    print(top_tacklers[["player", "team", "age", "tackles"]])