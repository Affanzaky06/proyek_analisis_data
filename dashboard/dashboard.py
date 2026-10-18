import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from pathlib import Path
from io import BytesIO


sns.set(style='whitegrid')


# Konfigurasi & konstanta (warna mengikuti notebook)
st.set_page_config(page_title='Bike Sharing Dashboard', page_icon='bike', layout='wide')

WARNA_HARI = {'Hari Kerja': 'blue', 'Akhir Pekan & Libur': 'green'}
WARNA_TIPE = {'casual': 'red', 'registered': 'orange'}
URUT_HARI = ['Hari Kerja', 'Akhir Pekan & Libur']
LABEL_SEGMEN = ['Dini Hari (00-05)', 'Pagi Sibuk (06-09)', 'Siang (10-15)',
                'Sore Sibuk (16-19)', 'Malam (20-23)']
PILIHAN_TIPE = {'Total (casual + registered)': 'cnt', 'Casual': 'casual', 'Registered': 'registered'}



# Helper function (pola yang sama dengan Latihan_Streamlit.py)
def create_daily_df(df):
    """Agregasi per hari: total penyewaan casual, registered, dan jenis harinya."""
    daily_df = df.groupby('dteday').agg({
        'casual': 'sum',
        'registered': 'sum',
        'cnt': 'sum',
        'workingday': 'first'
    }).reset_index()
    daily_df['day_type'] = np.where(daily_df['workingday'] == 1, 'Hari Kerja', 'Akhir Pekan & Libur')
    return daily_df


def create_hourly_pattern_df(df, kolom):
    """Rata-rata penyewaan per jam untuk tiap jenis hari."""
    return df.pivot_table(index='hr', columns='day_type', values=kolom, aggfunc='mean')


def create_composition_df(daily_df):
    """Rata-rata penyewaan harian casual & registered serta porsinya per jenis hari."""
    rata_df = daily_df.groupby('day_type')[['casual', 'registered', 'cnt']].mean()
    rata_df['porsi_casual'] = rata_df['casual'] / rata_df['cnt'] * 100
    rata_df['porsi_registered'] = rata_df['registered'] / rata_df['cnt'] * 100
    return rata_df.reindex([j for j in URUT_HARI if j in rata_df.index])


def create_segment_df(df, jenis_hari):
    """Kontribusi (%) tiap segmen waktu terhadap total penyewaan tiap tipe pengguna."""
    segmen_df = (df[df['day_type'] == jenis_hari]
                 .groupby('segmen_waktu', observed=True)[['casual', 'registered']].sum()
                 .reindex(LABEL_SEGMEN))
    return segmen_df / segmen_df.sum() * 100



# Load & siapkan data
@st.cache_data
def load_data():
    data_path = Path(__file__).resolve().parent / "main_data.csv"
    df = pd.read_csv(data_path, parse_dates=["dteday"])

    df['day_type'] = np.where(df['workingday'] == 1, 'Hari Kerja', 'Akhir Pekan & Libur')
    df['segmen_waktu'] = pd.cut(df['hr'], bins=[-1, 5, 9, 15, 19, 23], labels=LABEL_SEGMEN)
    return df.sort_values(['dteday', 'hr']).reset_index(drop=True)


all_df = load_data()
min_date = all_df['dteday'].min().date()
max_date = all_df['dteday'].max().date()


# Sidebar
with st.sidebar:
    rentang = st.date_input(
        label='Rentang Waktu',
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )
    st.title('Bike Sharing')
    st.caption('Capital Bikeshare, Washington D.C. (2011-2012)')

    st.markdown('---')
    st.markdown('**Keterangan**')
    st.markdown('- **Hari Kerja**: `workingday = 1`\n'
                '- **Akhir Pekan & Libur**: akhir pekan + libur resmi (`workingday = 0`)')

if not isinstance(rentang, (list, tuple)) or len(rentang) != 2:
    st.info('Pilih **tanggal awal dan tanggal akhir** pada filter Rentang Waktu di sidebar.')
    st.stop()

start_date, end_date = rentang
main_df = all_df[(all_df['dteday'] >= pd.Timestamp(start_date)) &
                 (all_df['dteday'] <= pd.Timestamp(end_date))]

if main_df.empty:
    st.warning('Tidak ada data pada rentang waktu yang dipilih.')
    st.stop()

daily_df = create_daily_df(main_df)
composition_df = create_composition_df(daily_df)


# Header & ringkasan
st.header('Dashboard Analisis Bike Sharing :bike:')
st.caption(f'Periode: {start_date:%d %b %Y} - {end_date:%d %b %Y} · {len(daily_df):,} hari data')

total_cnt = daily_df['cnt'].sum()
col1, col2, col3, col4 = st.columns(4)
col1.metric('Total Penyewaan', f'{total_cnt:,.0f}')
col2.metric('Rata-rata per Hari', f"{daily_df['cnt'].mean():,.0f}")
col3.metric('Pengguna Registered', f"{daily_df['registered'].sum() / total_cnt * 100:.1f}%")
col4.metric('Pengguna Casual', f"{daily_df['casual'].sum() / total_cnt * 100:.1f}%")


# Pertanyaan 1: pola jam
st.subheader('Pertanyaan 1: Pola Penyewaan per Jam')
st.write('Pada jam berapa permintaan sepeda mencapai puncak pada **hari kerja** dibandingkan '
         '**akhir pekan & libur**, dan berapa rata-rata penyewaan per jam pada jam puncak tersebut?')


pilihan = st.selectbox('Tipe pengguna yang ditampilkan', list(PILIHAN_TIPE.keys()))
kolom_tipe = PILIHAN_TIPE[pilihan]
pola_jam = create_hourly_pattern_df(main_df, kolom_tipe)

kolom_metrik = st.columns(3)
if 'Hari Kerja' in pola_jam.columns:
    hk = pola_jam['Hari Kerja'].dropna()
    pagi, sore = hk.loc[6:10], hk.loc[15:20]
    kolom_metrik[0].metric('Puncak Pagi · Hari Kerja', f'{pagi.idxmax():02d}:00',
                           f'{pagi.max():,.0f} sewa/jam', delta_color='off')
    kolom_metrik[1].metric('Puncak Sore · Hari Kerja', f'{sore.idxmax():02d}:00',
                           f'{sore.max():,.0f} sewa/jam', delta_color='off')
if 'Akhir Pekan & Libur' in pola_jam.columns:
    we = pola_jam['Akhir Pekan & Libur'].dropna()
    kolom_metrik[2].metric('Puncak · Akhir Pekan & Libur', f'{we.idxmax():02d}:00',
                           f'{we.max():,.0f} sewa/jam', delta_color='off')

fig, ax = plt.subplots(figsize=(16, 6))
for jenis in pola_jam.columns:
    seri = pola_jam[jenis]
    ax.plot(seri.index, seri.values, marker='o', linewidth=2.5, color=WARNA_HARI[jenis], label=jenis)
    # Hari kerja: tandai puncak pagi dan sore; akhir pekan & libur: satu puncak
    if jenis == 'Hari Kerja':
        jam_puncak_list = [seri.loc[6:10].idxmax(), seri.loc[15:20].idxmax()]
    else:
        jam_puncak_list = [seri.idxmax()]
    for jam_puncak in jam_puncak_list:
        ax.annotate(f'{jam_puncak:02d}:00 · {seri.loc[jam_puncak]:,.0f}', xy=(jam_puncak, seri.loc[jam_puncak]),
                    xytext=(jam_puncak, seri.loc[jam_puncak] + pola_jam.max().max() * 0.07), ha='center',
                    color=WARNA_HARI[jenis], fontweight='bold', fontsize=12)
ax.set_title(f'Rata-rata Penyewaan per Jam: {pilihan}', fontsize=18, fontweight='bold')
ax.set_xlabel('Jam dalam sehari', fontsize=13)
ax.set_ylabel('Rata-rata penyewaan per jam', fontsize=13)
ax.set_xticks(range(0, 24))
ax.set_ylim(0, pola_jam.max().max() * 1.2)
ax.legend(title='Jenis hari', loc='upper left')
sns.despine()
buffer = BytesIO()
fig.savefig(
    buffer,
    format="png",
    dpi=150,
    bbox_inches="tight"
)

st.image(buffer.getvalue())
plt.close(fig)

st.info('**Insight (seluruh periode):** hari kerja memiliki dua puncak komuter pukul 08:00 dan 17:00, '
        'sedangkan akhir pekan & libur memiliki satu puncak landai sekitar pukul 13:00.')


# Pertanyaan 2: komposisi pengguna

st.subheader('Pertanyaan 2: Volume dan Komposisi Pengguna Casual vs Registered')
st.write('Berapa selisih rata-rata penyewaan harian pengguna **casual** dan **registered** antara hari kerja '
         'dan hari libur, serta berapa porsi pengguna **casual** pada masing-masing jenis hari?')

if len(composition_df) < 2:
    st.warning('Rentang waktu yang dipilih hanya memuat satu jenis hari. '
               'Perluas rentang waktu agar hari kerja dan hari libur dapat dibandingkan.')
else:
    kerja, libur = composition_df.loc['Hari Kerja'], composition_df.loc['Akhir Pekan & Libur']
    delta_casual = (libur['casual'] / kerja['casual'] - 1) * 100
    delta_reg = (libur['registered'] / kerja['registered'] - 1) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric('Casual · Hari Libur (per hari)', f"{libur['casual']:,.0f}", f'{delta_casual:+.0f}% vs hari kerja')
    c2.metric('Registered · Hari Libur (per hari)', f"{libur['registered']:,.0f}", f'{delta_reg:+.0f}% vs hari kerja')
    c3.metric('Porsi Casual (Kerja → Libur)', f"{libur['porsi_casual']:.1f}%",
              f"{libur['porsi_casual'] - kerja['porsi_casual']:+.1f} poin dari {kerja['porsi_casual']:.1f}%")

    fig, axes = plt.subplots(1, 2, figsize=(20, 7))

    x = np.arange(len(composition_df))
    lebar = 0.36
    for k, tipe in enumerate(['casual', 'registered']):
        batang = axes[0].bar(x + (k - 0.5) * lebar, composition_df[tipe], lebar,
                             label=tipe.capitalize(), color=WARNA_TIPE[tipe])
        for b in batang:
            axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + composition_df['registered'].max() * 0.01,
                         f'{b.get_height():,.0f}', ha='center', fontweight='bold', fontsize=13)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(composition_df.index, fontsize=13)
    axes[0].set_ylim(0, composition_df['registered'].max() * 1.15)
    axes[0].set_ylabel('Rata-rata penyewaan per hari', fontsize=13)
    axes[0].set_title('Rata-rata Penyewaan Harian per Tipe Pengguna', fontsize=16, fontweight='bold')
    axes[0].legend(title='Tipe pengguna')

    axes[1].barh(composition_df.index, composition_df['porsi_registered'],
                 color=WARNA_TIPE['registered'], label='Registered')
    axes[1].barh(composition_df.index, composition_df['porsi_casual'],
                 left=composition_df['porsi_registered'], color=WARNA_TIPE['casual'], label='Casual')
    for i, jenis in enumerate(composition_df.index):
        axes[1].text(composition_df.loc[jenis, 'porsi_registered'] / 2, i,
                     f"{composition_df.loc[jenis, 'porsi_registered']:.1f}%",
                     ha='center', va='center', color='white', fontweight='bold', fontsize=14)
        axes[1].text(composition_df.loc[jenis, 'porsi_registered'] + composition_df.loc[jenis, 'porsi_casual'] / 2, i,
                     f"{composition_df.loc[jenis, 'porsi_casual']:.1f}%",
                     ha='center', va='center', color='white', fontweight='bold', fontsize=14)
    axes[1].set_xlim(0, 100)
    axes[1].set_xlabel('Persentase dari total penyewaan harian (%)', fontsize=13)
    axes[1].set_title('Komposisi Pengguna per Jenis Hari', fontsize=16, fontweight='bold')
    axes[1].tick_params(axis='y', labelsize=13)
    axes[1].legend(title='Tipe pengguna', loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
    sns.despine()
    plt.tight_layout()
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )
    st.image(buffer.getvalue())
    plt.close(fig)

    st.info('**Insight (seluruh periode):** pengguna *casual* naik ±126% pada hari libur (607 → 1.371 per hari), '
            'sedangkan *registered* turun ±26% (3.978 → 2.959). Porsi *casual* naik dari 13,2% menjadi 31,7%.')


# Analisis lanjutan

st.subheader('Analisis Lanjutan: Segmen Waktu menurut Tipe Pengguna')
st.write('Pengelompokan jam secara manual (*manual grouping*): Dini Hari 00-05, Pagi Sibuk 06-09, '
         'Siang 10-15, Sore Sibuk 16-19, dan Malam 20-23.')

jenis_pilihan = st.radio('Jenis hari', URUT_HARI, horizontal=True)
data_jenis = main_df[main_df['day_type'] == jenis_pilihan]

if data_jenis.empty:
    st.warning(f'Tidak ada data {jenis_pilihan} pada rentang waktu yang dipilih.')
else:
    segmen_df = create_segment_df(main_df, jenis_pilihan)
    jam_tipe = data_jenis.groupby('hr')[['casual', 'registered']].mean()

    col_a, col_b = st.columns(2)

    with col_a:
        fig, ax = plt.subplots(figsize=(11, 7))
        x = np.arange(len(segmen_df))
        for k, tipe in enumerate(['casual', 'registered']):
            batang = ax.bar(x + (k - 0.5) * 0.38, segmen_df[tipe], 0.38,
                            label=tipe.capitalize(), color=WARNA_TIPE[tipe])
            for b in batang:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f'{b.get_height():.1f}%',
                        ha='center', fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace(' (', '\n(') for s in segmen_df.index], fontsize=11)
        ax.set_ylabel('Kontribusi terhadap total (%)', fontsize=12)
        ax.set_ylim(0, segmen_df.max().max() * 1.2)
        ax.set_title(f'Kontribusi Segmen Waktu · {jenis_pilihan}', fontsize=15, fontweight='bold')
        ax.legend(title='Tipe pengguna')
        sns.despine()
        st.pyplot(fig)

    with col_b:
        fig, ax = plt.subplots(figsize=(11, 7))
        for tipe in ['registered', 'casual']:
            ax.plot(jam_tipe.index, jam_tipe[tipe], marker='o', linewidth=2.5,
                    color=WARNA_TIPE[tipe], label=tipe.capitalize())
            jam_p = jam_tipe[tipe].idxmax()
            ax.annotate(f'{jam_p:02d}:00 · {jam_tipe[tipe].max():,.0f}', xy=(jam_p, jam_tipe[tipe].max()),
                        xytext=(jam_p, jam_tipe[tipe].max() + jam_tipe.max().max() * 0.08), ha='center',
                        color=WARNA_TIPE[tipe], fontweight='bold', fontsize=12)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xlabel('Jam dalam sehari', fontsize=12)
        ax.set_ylabel('Rata-rata penyewaan per jam', fontsize=12)
        ax.set_ylim(0, jam_tipe.max().max() * 1.25)
        ax.set_title(f'Pola Jam per Tipe Pengguna · {jenis_pilihan}', fontsize=15, fontweight='bold')
        ax.legend(title='Tipe pengguna', loc='upper left')
        sns.despine()
        st.pyplot(fig)

st.info('**Insight (seluruh periode):** *registered* hari kerja memuncak pukul 17:00 (±468 sewa/jam) dan 08:00, '
        'sedangkan *casual* hari libur memuncak pukul 14:00 (±140 sewa/jam). Segmen siang (10:00-15:00) '
        'menyumbang 52,9% penyewaan *casual* pada hari libur.')


# Kesimpulan & rekomendasi

st.subheader('Kesimpulan & Rekomendasi')
with st.expander('Lihat kesimpulan dan rekomendasi action item', expanded=False):
    st.markdown("""
**Kesimpulan**
- **Pertanyaan 1:** hari kerja memiliki dua puncak komuter pada **08:00 (±477 sewa/jam)** dan **17:00 (±525 sewa/jam)**,
  sedangkan akhir pekan & libur memiliki satu puncak landai pada **13:00 (±373 sewa/jam)**.
- **Pertanyaan 2:** *casual* naik **+126%** pada hari libur sedangkan *registered* turun **-26%**; porsi *casual* naik
  dari **13,2%** menjadi **31,7%**. Hari libur (31,6% dari seluruh hari) menyumbang **51,1%** penyewaan *casual*.

**Rekomendasi**
- **Rebalancing:** pindahkan sepeda ke area perkantoran/transit sebelum 07:30 dan 16:30 pada hari kerja, dan ke
  area wisata/taman sebelum 11:00 pada akhir pekan.
- **Konversi casual menjadi member:** tawarkan membership (trial/diskon) pada Sabtu-Minggu pukul 11:00-16:00.
- **Perawatan armada:** lakukan servis massal pada hari kerja pukul 10:00-15:00 dan dini hari.
""")

st.caption('Sumber data: Fanaee-T & Gama (2013), Bike Sharing Dataset · Proyek Analisis Data - Abyaz Affanzaky Shanahan')