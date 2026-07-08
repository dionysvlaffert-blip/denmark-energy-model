from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.fixxed_values import COUNTRY_CODE

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


TIME_STEP_HOURS = 1.0



def load_weather_profiles_per_region(year, config):
	"""
	Load per-region weather profile tables for one year.

	Output order: wind_on, wind_off, solar DataFrames.
	"""
	year = int(year)
	base = config.weather_profiles_output_dir / str(year)

	solar_per_reg = pd.read_csv(
		base / f"solar_p_max_pu_level1_{year}.csv",
		index_col="snapshot",
		parse_dates=True,
	)
	wind_on_per_reg = pd.read_csv(
		base / f"onshore_wind_p_max_pu_level1_{year}.csv",
		index_col="snapshot",
		parse_dates=True,
	)
	wind_off_per_reg = pd.read_csv(
		base / f"offshore_wind_p_max_pu_level1_{year}.csv",
		index_col="snapshot",
		parse_dates=True,
	)

	return wind_on_per_reg, wind_off_per_reg, solar_per_reg


def load_agg_weather_dk(year, config):
	"""
	Load weather profiles for one year and aggregate to DK mean.

	Output: DataFrame with columns wind_on, wind_off, solar.
	"""
	wind_on_per_reg, wind_off_per_reg, solar_per_reg = load_weather_profiles_per_region(year, config)

	agg_weather_dk = pd.DataFrame(
		{
			"wind_on": wind_on_per_reg.mean(axis=1),
			"wind_off": wind_off_per_reg.mean(axis=1),
			"solar": solar_per_reg.mean(axis=1),
		}
	)

	return agg_weather_dk
def calc_cap_fac_solar_wind(df, scale_wind=1.0, scale_solar=1.0):
	"""
	Calculate the capacity factor for solar and wind. Use scale factors to allow for different weighting of wind and solar. 
	This is applied to get cap factor series that allows over installing of technology.

	Inputs: DataFrame with columns wind_on, wind_off, solar.
	"""
	cap_fac_mean = (df["wind_on"] * scale_wind + df["solar"] * scale_solar) / 2
	return cap_fac_mean

def calc_full_load_hours_for_year(agg_weather_dk, year=None):
	"""
	Calculate full load hours from aggregated weather profiles.

	Inputs: DataFrame with columns wind_on, wind_off, solar and datetime index.
	Output: pandas Series with wind_on, wind_off, solar full load hours.
	"""
	if len(agg_weather_dk.index) < 2:
		raise ValueError("Need at least two timestamps to calculate time step hours")

	time_step_hours = TIME_STEP_HOURS

	full_load_hours = agg_weather_dk.sum(axis=0) * time_step_hours
	if year is not None:
		full_load_hours.name = int(year)

	return full_load_hours


def calc_rolling_variances_weather(agg_weather_dk):
	"""
	Calculate rolling variances for 1-day and 7-day windows.

	Input: DataFrame agg_weather_dk with datetime index.
	Output: DataFrame with columns *_var_1d and *_var_7d.
	"""
	if not isinstance(agg_weather_dk.index, pd.DatetimeIndex):
		raise ValueError("agg_weather_dk index must be a DatetimeIndex")

	weather_cols = [col for col in ["wind_on", "wind_off", "solar"] if col in agg_weather_dk.columns]
	if not weather_cols:
		raise ValueError("agg_weather_dk must contain at least one of: wind_on, wind_off, solar")

	data = agg_weather_dk[weather_cols].sort_index()

	rolling_var_1d = data.rolling("1D").var().add_suffix("_var_1d")
	rolling_var_7d = data.rolling("7D").var().add_suffix("_var_7d")

	return pd.concat([rolling_var_1d, rolling_var_7d], axis=1)


def calc_fft_weather_signal(agg_weather_dk, config):
	"""
	Compute FFT of mean weather capacity factor.

	Input: DataFrame with datetime index and column cap_factor_weather.
	Output: DataFrame with frequency_per_hour and fft_complex.
	"""
	series = agg_weather_dk["cap_factor_weather"]

	values = series.to_numpy(dtype=float)

	n = len(values)
	frequencies_per_hour = np.fft.rfftfreq(n=n, d=TIME_STEP_HOURS)
	fft_values = np.fft.rfft(values)

	return pd.DataFrame(
		{
			"frequency_per_hour": frequencies_per_hour,
			"fft_complex": fft_values,
		}
	)


def calc_correlation_wind_solar(agg_weather_dk):
	"""
	Calculate linear correlation between onshore wind and solar.

	Input: DataFrame with columns wind_on and solar.
	Output: float Pearson correlation coefficient.
	"""
	return agg_weather_dk["wind_on"].corr(agg_weather_dk["solar"])


def calc_residual_load(load_norm, agg_weather_dk, year, scale_wind=1.5, scale_solar=2.0):
	"""
	Calculate residual load = normalized load - weighted mean capacity factor.

	Inputs: normalized load Series, aggregated weather DataFrame and target year.
	Output: pandas Series residual_load aligned to agg_weather_dk index.
	"""
	load_year = load_norm.copy()
	load_year.index = load_year.index.map(lambda ts: ts.replace(year=int(year)))
	load_year = load_year.reindex(agg_weather_dk.index)

	cap_factor_weighted = calc_cap_fac_solar_wind(
		agg_weather_dk,
		scale_wind=scale_wind,
		scale_solar=scale_solar,
	)

	residual_load = load_year - cap_factor_weighted
	residual_load.name = "residual_load"
	return residual_load


def count_dunkelflaute_sections(residual_load, threshold=0.0):
	"""
	Count consecutive residual-load events in duration classes.

	A dunkelflaute event is defined as residual_load > threshold.
	Duration classes are minimum durations in days: >=1, >=2, >=7, >=14.

	Input: residual load Series with DatetimeIndex.
	Output: pandas Series with counts per duration class.
	"""
	mask = residual_load > threshold
	group_id = mask.ne(mask.shift(fill_value=False)).cumsum()
	event_lengths_steps = mask.groupby(group_id).sum()
	event_lengths_days = event_lengths_steps[event_lengths_steps > 0] * TIME_STEP_HOURS / 24.0

	return pd.Series(
		{
			"dunkelflaute_ge_1d": int((event_lengths_days >= 1).sum()),
			"dunkelflaute_ge_2d": int((event_lengths_days >= 2).sum()),
			"dunkelflaute_ge_7d": int((event_lengths_days >= 7).sum()),
			"dunkelflaute_ge_14d": int((event_lengths_days >= 14).sum()),
		},
		dtype=int,
	)


def _as_dataframe_by_year(series_or_df_by_year):
	"""Convert {year: Series/DataFrame-row} mapping into a comparable DataFrame."""
	rows = {}
	for year, value in series_or_df_by_year.items():
		if isinstance(value, pd.Series):
			rows[year] = value
		elif isinstance(value, dict):
			rows[year] = pd.Series(value)
		else:
			rows[year] = pd.Series(value)

	out = pd.DataFrame(rows).T.sort_index()
	out.index.name = "year"
	return out


def plot_compare_full_load_hours(full_load_hours_by_year):
	"""
	Plot full-load-hours comparison over years as grouped bars.

	Input: dict year -> Series with full load hours.
	Output: matplotlib figure, axis.
	"""
	data = _as_dataframe_by_year(full_load_hours_by_year)
	data = data.drop(columns=["cap_factor_weather", "residual_load"], errors="ignore")
	fig, ax = plt.subplots(figsize=(10, 5))
	data.plot(kind="bar", ax=ax)
	ax.set_title("Full Load Hours by Year")
	ax.set_xlabel("Year")
	ax.set_ylabel("Hours")
	ax.legend(loc="best")
	fig.tight_layout()
	return fig, ax


def plot_compare_dunkelflaute_counts(dunkelflaute_counts_by_year):
	"""
	Plot dunkelflaute count comparison over years as grouped bars.

	Input: dict year -> Series with dunkelflaute counts.
	Output: matplotlib figure, axis.
	"""
	data = _as_dataframe_by_year(dunkelflaute_counts_by_year)
	fig, ax = plt.subplots(figsize=(10, 5))
	data.plot(kind="bar", ax=ax)
	ax.set_title("Dunkelflaute Counts by Year")
	ax.set_xlabel("Year")
	ax.set_ylabel("Count")
	ax.legend(loc="best")
	fig.tight_layout()
	return fig, ax


def plot_compare_correlations(correlation_by_year):
	"""
	Plot wind-solar correlation values across years.

	Input: dict year -> float correlation value.
	Output: matplotlib figure, axis.
	"""
	data = pd.Series(correlation_by_year).sort_index()
	fig, ax = plt.subplots(figsize=(8, 4))
	data.plot(kind="bar", ax=ax)
	ax.set_title("Wind-Solar Correlation by Year")
	ax.set_xlabel("Year")
	ax.set_ylabel("Correlation")
	ax.axhline(0, color="black", linewidth=1)
	fig.tight_layout()
	return fig, ax


def plot_compare_time_series(agg_weather_by_year, column="residual_load", rolling_hours=24):
	"""
	Compare one weather metric over the year for multiple years.

	Input: dict year -> agg_weather DataFrame, target column and rolling window.
	Output: matplotlib figure, axis.
	"""
	fig, ax = plt.subplots(figsize=(11, 5))

	for year, df in sorted(agg_weather_by_year.items()):
		series = df[column]
		if rolling_hours and rolling_hours > 1:
			series = series.rolling(rolling_hours, min_periods=1).mean()
		ax.plot(series.values, label=str(year), linewidth=1.5)

	ax.set_title(f"{column} Comparison by Year")
	ax.set_xlabel("Time step")
	ax.set_ylabel(column)
	ax.legend(loc="best")
	fig.tight_layout()
	return fig, ax


def plot_compare_fft_amplitude(fft_by_year, max_frequency_per_hour=0.02):
	"""
	Compare FFT amplitude spectra for multiple years as bar columns.

	Input: dict year -> fft DataFrame with frequency_per_hour and fft_complex.
	Output: matplotlib figure, axis with x-axis in period days.
	"""
	fig, ax = plt.subplots(figsize=(10, 5))
	prepared = []

	for year, fft_df in sorted(fft_by_year.items()):
		data = fft_df.copy()
		data = data[data["frequency_per_hour"] > 0]
		if max_frequency_per_hour is not None:
			data = data[data["frequency_per_hour"] <= max_frequency_per_hour]
		if data.empty:
			continue

		period_days = 1.0 / (data["frequency_per_hour"].to_numpy() * 24.0)
		amplitude = np.abs(data["fft_complex"].to_numpy())
		sort_idx = np.argsort(period_days)
		prepared.append((year, period_days[sort_idx], amplitude[sort_idx]))

	n_series = len(prepared)
	if n_series == 0:
		ax.set_title("FFT Amplitude Comparison by Year")
		ax.set_xlabel("Period [days]")
		ax.set_ylabel("Amplitude")
		fig.tight_layout()
		return fig, ax

	all_x = np.concatenate([x for _, x, _ in prepared])
	if len(np.unique(all_x)) > 1:
		dx = np.diff(np.unique(np.sort(all_x)))
		base_width = max(np.median(dx) * 0.8, 1e-6)
	else:
		base_width = 0.2

	bar_width = base_width / n_series
	for idx, (year, period_days, amplitude) in enumerate(prepared):
		offset = (idx - (n_series - 1) / 2.0) * bar_width
		ax.bar(period_days + offset, amplitude, width=bar_width, alpha=0.7, label=str(year), align="center")

	# Auto-zoom to make the dominant FFT region easier to inspect.
	all_y = np.concatenate([y for _, _, y in prepared])
	finite_x = all_x[np.isfinite(all_x)]
	finite_y = all_y[np.isfinite(all_y)]
	if finite_x.size > 0:
		x_min = np.percentile(finite_x, 2)
		x_max = np.percentile(finite_x, 98)
		if x_max > x_min:
			ax.set_xlim(x_min, x_max)
	if finite_y.size > 0:
		y_max = np.percentile(finite_y, 99)
		if y_max > 0:
			ax.set_ylim(0, y_max * 1.05)

	ax.set_title("FFT Amplitude Comparison by Year")
	ax.set_xlabel("Period [days]")
	ax.set_ylabel("Amplitude")
	ax.legend(loc="best")
	fig.tight_layout()
	return fig, ax


def plot_compare_mean_rolling_variance_time(rolling_variances_by_year, suffix="var_7d"):
	"""
	Plot time-series of mean rolling variance by year for selected window.

	Input: dict year -> rolling variance DataFrame, suffix var_1d or var_7d.
	Output: matplotlib figure, axis.
	"""
	fig, ax = plt.subplots(figsize=(11, 5))
	max_len = 0

	for year, df in sorted(rolling_variances_by_year.items()):
		cols = [c for c in df.columns if c.endswith(suffix)]
		if not cols:
			continue
		mean_series = df[cols].mean(axis=1)
		x_days = np.arange(len(mean_series)) * TIME_STEP_HOURS / 24.0
		ax.plot(x_days, mean_series.values, label=str(year), linewidth=1.5)
		max_len = max(max_len, len(mean_series))

	if max_len > 0:
		ax.set_xlim(0, (max_len - 1) * TIME_STEP_HOURS / 24.0)

	ax.set_title(f"Mean Rolling Variance Over Time ({suffix})")
	ax.set_xlabel("Time in Year [days]")
	ax.set_ylabel("Mean variance")
	ax.legend(loc="best")
	fig.tight_layout()
	return fig, ax




