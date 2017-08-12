# -*- coding: utf-8 -*-
"""
Created on Fri May 12 06:55:57 2017

@author: tsansom
"""

def inpolygon(polygon, xp, yp):
    return np.array([Point(x,y).intersects(polygon) for x,y in zip(xp,yp)],dtype=np.bool)

import pandas as pd
import os
import matplotlib.pyplot as plt
from shapely.geometry.polygon import LinearRing
from matplotlib.animation import FuncAnimation
import matplotlib.animation as animation
import cartopy.crs as ccrs
from cartopy.io.shapereader import Reader
import matplotlib.gridspec as gridspec
import sys
import tbtools as tbt
import numpy as np
from shapely.geometry import Point
from matplotlib.mlab import griddata
from calendar import month_name

#cb = 'CBclosed'
#month = '0401'
CB = ['CBclosed', 'CBopen']
months = ['0401', '0501', '0601', '0701', '0801']
years = ['1993', '1995', '1997', '2007', '2009', '2011']

extent = (-97.4, -96.6, 27.7, 28.44)

for cb in CB:
    for month in months:
        if cb == 'CBclosed':
            continue
        elif cb == 'CBopen' and month in ['0401']:
            continue
        #for cb in CB:
        ptrac_path = r'F:\home\tsansom\Projects\5Bay\TNC_PTrac\{0}\ptrac'.format(cb)
        shp_path = r'T:\baysestuaries\USERS\TSansom\TxBLEND\TNC_PTrac\{0}.shp'.format(cb)
        #    for month in months:
        ##############################################################################
        '''
        Check if new data needs to be read in:
        '''
        if 'data' in vars():
            if 'working_month' not in vars():
                working_month = ''
            if month != working_month:
                del data
        if 'mask' in vars():
            if 'working_scenario' not in vars():
                working_scenario = ''
            if cb != working_scenario:
                del mask
        ##############################################################################
        '''
        Read the data
        '''
        if 'data' not in vars():
            data = {}
            working_month = month
            for year in years:
                print('Reading data for {0} - {1} - {2}'.format(cb,year,month))
                lon_path = os.path.join(ptrac_path, 'YR'+year, month, '{0}_{1}_{2}_lon.csv'.format(cb[:3].lower(), year, month))
                lat_path = os.path.join(ptrac_path, 'YR'+year, month, '{0}_{1}_{2}_lat.csv'.format(cb[:3].lower(), year, month))
                outflw1_dir = os.path.join(ptrac_path, 'YR'+year, month)
                input_path = os.path.join(ptrac_path, 'YR'+year, month, 'input')
                avesalD_path = os.path.join(ptrac_path, 'YR'+year, month, 'avesalD.w')
                print('\tReading particle longitude data')
                lon_data = pd.read_csv(lon_path, parse_dates=True, index_col=0)
                print('\tReading particle latitude data')
                lat_data = pd.read_csv(lat_path, parse_dates=True, index_col=0)
                print('\tReading outflw1 data')
                outflw1_data = tbt.read.outflw1(outflw1_dir)
                for k in outflw1_data:
                    outflw1_data[k]['u'] = -1 * outflw1_data[k]['velocity'] * np.sin(np.deg2rad(outflw1_data[k]['direction']))
                    outflw1_data[k]['v'] = -1 * outflw1_data[k]['velocity'] * np.cos(np.deg2rad(outflw1_data[k]['direction']))
                print('\tReading node coordinates')
                coords = tbt.read.coords(input_path)
                print('\tReading daily average salinity\n')
                avesalD_data = tbt.read.avesalD(avesalD_path)
                avesalD_nodes = coords[(coords['lon'] > extent[0]) &
                                       (coords['lon'] < extent[1]) &
                                       (coords['lat'] > extent[2]) &
                                       (coords['lat'] < extent[3])].index.tolist()
                avesalD_data = avesalD_data[avesalD_nodes]
                data[year] = {'lat': lat_data,
                            'lon': lon_data,
                            'outflw1': outflw1_data,
                            'avesalD': avesalD_data}
        ##############################################################################
        '''
        Set up the daily average salinity grid
        '''
        if 'mask' not in vars():
            working_scenario = cb
            avesalD_coords = coords.ix[avesalD_nodes]
            lon = np.array(avesalD_coords['lon'])
            lat = np.array(avesalD_coords['lat'])
            loni = np.linspace(min(lon), max(lon), 100)
            lati = np.linspace(min(lat), max(lat), 100)
            glon, glat = np.meshgrid(loni, lati)
            
            shp = Reader(shp_path)
            geoms = list(shp.geometries())
            max_area = 0
            max_area_id = 0
            for i in range(len(geoms)):
                if geoms[i].area > max_area:
                    max_area = geoms[i].area
                    max_area_id = i
                    polygon = geoms[i]
            mask = inpolygon(polygon, glon.ravel(), glat.ravel())
            mask = mask.reshape(glon.shape)
        ##############################################################################
        '''
        Make the base map
        '''
        lats = [28.142815, 28.142622, 28.128572, 28.128588]
        lons = [-97.057931, -97.041549, -97.041542, -97.057923]
        ring = LinearRing(list(zip(lons,lats)))
        
        gs = gridspec.GridSpec(2,6)
        
        fig = plt.figure(figsize=(13.15,9))
        
        ax93 = plt.subplot(gs[0,:2], projection=ccrs.Miller())
        ax95 = plt.subplot(gs[0,2:4], projection=ccrs.Miller())
        ax09 = plt.subplot(gs[0,4:], projection=ccrs.Miller())
        ax07 = plt.subplot(gs[1,:2], projection=ccrs.Miller())
        ax97 = plt.subplot(gs[1,2:4], projection=ccrs.Miller())
        ax11 = plt.subplot(gs[1,4:], projection=ccrs.Miller())
        
        axes = [ax93, ax95, ax97, ax07, ax09, ax11]
        
        for ax,yr in zip(axes, years):
            ax.set_extent(extent, ccrs.Miller())
            ax.add_geometries(shp.geometries(), ccrs.Miller(), facecolor='none', edgecolor='black')
            ax.add_geometries([ring], ccrs.Miller(), facecolor='none', edgecolor='black')
        #    ax.text(0.02, 0.93, yr, fontsize=14, transform = ax.transAxes, bbox=dict(facecolor='lightgray', alpha=1))
            if yr == '1993':
                ax.set_title(r'Wet Years', fontsize=16, style='italic', weight='bold', loc='left')
            elif yr == '1995':
                ax.set_title(r'Median Years', fontsize=16, style='italic', weight='bold', loc='left')
            elif yr == '2009':
                ax.set_title(r'Dry Years', fontsize=16, style='italic', weight='bold', loc='left')
        
        fig.suptitle(r'{0} 1 Release'.format(month_name[int(month[:2])]), fontsize=24, x = 0.01, y = 0.99, horizontalalignment='left', verticalalignment='top')
        plt.tight_layout()
        fig.subplots_adjust(top=0.9)
        ##############################################################################
        '''
        Set up the velocity check nodes
        '''
        cn = list(map(int, list(data['1993']['outflw1'].keys())))
        cknodes = coords.ix[cn]
        ##############################################################################
        '''
        Now animate the particles
        '''
        index93 = data['1993']['lon'].index[0]
        index95 = data['1995']['lon'].index[0]
        index97 = data['1997']['lon'].index[0]
        index07 = data['2007']['lon'].index[0]
        index09 = data['2009']['lon'].index[0]
        index11 = data['2011']['lon'].index[0]
        
        time_text93 = ax93.text(0.02, 0.93, index93, bbox=dict(facecolor='lightgray', alpha=1), fontsize=14, weight='medium', transform=ax93.transAxes)
        time_text95 = ax95.text(0.02, 0.93, index95, bbox=dict(facecolor='lightgray', alpha=1), fontsize=14, weight='medium', transform=ax95.transAxes)
        time_text97 = ax97.text(0.02, 0.93, index97, bbox=dict(facecolor='lightgray', alpha=1), fontsize=14, weight='medium', transform=ax97.transAxes)
        time_text07 = ax07.text(0.02, 0.93, index07, bbox=dict(facecolor='lightgray', alpha=1), fontsize=14, weight='medium', transform=ax07.transAxes)
        time_text09 = ax09.text(0.02, 0.93, index09, bbox=dict(facecolor='lightgray', alpha=1), fontsize=14, weight='medium', transform=ax09.transAxes)
        time_text11 = ax11.text(0.02, 0.93, index11, bbox=dict(facecolor='lightgray', alpha=1), fontsize=14, weight='medium', transform=ax11.transAxes)
        
        sctr93 = ax93.scatter(data['1993']['lon'].ix[0], data['1993']['lat'].ix[0])
        sctr95 = ax95.scatter(data['1995']['lon'].ix[0], data['1995']['lat'].ix[0])
        sctr97 = ax97.scatter(data['1997']['lon'].ix[0], data['1997']['lat'].ix[0])
        sctr07 = ax07.scatter(data['2007']['lon'].ix[0], data['2007']['lat'].ix[0])
        sctr09 = ax09.scatter(data['2009']['lon'].ix[0], data['2009']['lat'].ix[0])
        sctr11 = ax11.scatter(data['2011']['lon'].ix[0], data['2011']['lat'].ix[0])
        
        u93 = [data['1993']['outflw1'][k]['u'][0] for k in data['1993']['outflw1']]
        v93 = [data['1993']['outflw1'][k]['v'][0] for k in data['1993']['outflw1']]
        quiv93 = ax93.quiver(cknodes['lon'], cknodes['lat'], u93, v93, scale=8, facecolor='white', edgecolors='black', linewidth=0.3)
        u95 = [data['1995']['outflw1'][k]['u'][0] for k in data['1995']['outflw1']]
        v95 = [data['1995']['outflw1'][k]['v'][0] for k in data['1995']['outflw1']]
        quiv95 = ax95.quiver(cknodes['lon'], cknodes['lat'], u95, v95, scale=8, facecolor='white', edgecolors='black', linewidth=0.3)
        u97 = [data['1997']['outflw1'][k]['u'][0] for k in data['1997']['outflw1']]
        v97 = [data['1997']['outflw1'][k]['v'][0] for k in data['1997']['outflw1']]
        quiv97 = ax97.quiver(cknodes['lon'], cknodes['lat'], u97, v97, scale=8, facecolor='white', edgecolors='black', linewidth=0.3)
        u07 = [data['2007']['outflw1'][k]['u'][0] for k in data['2007']['outflw1']]
        v07 = [data['2007']['outflw1'][k]['v'][0] for k in data['2007']['outflw1']]
        quiv07 = ax07.quiver(cknodes['lon'], cknodes['lat'], u07, v07, scale=8, facecolor='white', edgecolors='black', linewidth=0.3)
        u09 = [data['2009']['outflw1'][k]['u'][0] for k in data['2009']['outflw1']]
        v09 = [data['2009']['outflw1'][k]['v'][0] for k in data['2009']['outflw1']]
        quiv09 = ax09.quiver(cknodes['lon'], cknodes['lat'], u09, v09, scale=8, facecolor='white', edgecolors='black', linewidth=0.3)
        u11 = [data['2011']['outflw1'][k]['u'][0] for k in data['2011']['outflw1']]
        v11 = [data['2011']['outflw1'][k]['v'][0] for k in data['2011']['outflw1']]
        quiv11 = ax11.quiver(cknodes['lon'], cknodes['lat'], u11, v11, scale=8, facecolor='white', edgecolors='black', linewidth=0.3)
        
        #qk = plt.quiverkey(quiv09, 1.1, 1.1, 1,'1 foot per second\n(fps)', bbox=dict(facecolor='lightgray', alpha=1))
        qk = plt.quiverkey(quiv09, 0.93, 0.92, 1, 'Velocity Vectors\n' + r'$1 \frac{ft}{s}$', coordinates='figure', fontproperties={'size': 14})
        
        sal93 = np.array(data['1993']['avesalD'].ix[0])
        sal95 = np.array(data['1995']['avesalD'].ix[0])
        sal97 = np.array(data['1997']['avesalD'].ix[0])
        sal07 = np.array(data['2007']['avesalD'].ix[0])
        sal09 = np.array(data['2009']['avesalD'].ix[0])
        sal11 = np.array(data['2011']['avesalD'].ix[0])
        sali93 = griddata(lon, lat, sal93, loni, lati, interp='linear')
        sali95 = griddata(lon, lat, sal95, loni, lati, interp='linear')
        sali97 = griddata(lon, lat, sal97, loni, lati, interp='linear')
        sali07 = griddata(lon, lat, sal07, loni, lati, interp='linear')
        sali09 = griddata(lon, lat, sal09, loni, lati, interp='linear')
        sali11 = griddata(lon, lat, sal11, loni, lati, interp='linear')
        sali93.mask = ~mask
        sali95.mask = ~mask
        sali97.mask = ~mask
        sali07.mask = ~mask
        sali09.mask = ~mask
        sali11.mask = ~mask
        levels = np.arange(0, 30.5, 0.5)
        ticks = np.arange(0, 30.5, 2)
        contf93 = ax93.contourf(loni, lati, sali93, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, levels=levels, extend='max', alpha=0.7)
        contf95 = ax95.contourf(loni, lati, sali95, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, levels=levels, extend='max', alpha=0.7)
        contf97 = ax97.contourf(loni, lati, sali97, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, levels=levels, extend='max', alpha=0.7)
        contf07 = ax07.contourf(loni, lati, sali07, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, levels=levels, extend='max', alpha=0.7)
        contf09 = ax09.contourf(loni, lati, sali09, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, levels=levels, extend='max', alpha=0.7)
        contf11 = ax11.contourf(loni, lati, sali11, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, levels=levels, extend='max', alpha=0.7)
        
        fig.subplots_adjust(right=0.92)
        cbar_ax = fig.add_axes([0.93, 0.038, 0.03, 0.84])
        fig.colorbar(contf93, cax=cbar_ax, ticks=ticks, label='Salinity (ppt)')
        
        def update(i):
            
            global sctr93, sctr95, sctr97, sctr07, sctr09, sctr11
            sctr93.remove()
            sctr95.remove()
            sctr97.remove()
            sctr07.remove()
            sctr09.remove()
            sctr11.remove()
            
            index93 = data['1993']['lon'].index[i]
            index95 = data['1995']['lon'].index[i]
            index97 = data['1997']['lon'].index[i]
            index07 = data['2007']['lon'].index[i]
            index09 = data['2009']['lon'].index[i]
            index11 = data['2011']['lon'].index[i]
            
            sctr93 = ax93.scatter(data['1993']['lon'].ix[i], data['1993']['lat'].ix[i], marker='.', facecolor='lime', edgecolor='k', linewidth=.1, s=25)
            sctr95 = ax95.scatter(data['1995']['lon'].ix[i], data['1995']['lat'].ix[i], marker='.', facecolor='lime', edgecolor='k', linewidth=.1, s=25)
            sctr97 = ax97.scatter(data['1997']['lon'].ix[i], data['1997']['lat'].ix[i], marker='.', facecolor='lime', edgecolor='k', linewidth=.1, s=25)
            sctr07 = ax07.scatter(data['2007']['lon'].ix[i], data['2007']['lat'].ix[i], marker='.', facecolor='lime', edgecolor='k', linewidth=.1, s=25)
            sctr09 = ax09.scatter(data['2009']['lon'].ix[i], data['2009']['lat'].ix[i], marker='.', facecolor='lime', edgecolor='k', linewidth=.1, s=25)
            sctr11 = ax11.scatter(data['2011']['lon'].ix[i], data['2011']['lat'].ix[i], marker='.', facecolor='lime', edgecolor='k', linewidth=.1, s=25)
            
            if index93 in data['1993']['outflw1'][str(cn[0])].index:
                u93 = [data['1993']['outflw1'][k]['u'].loc[index93] for k in data['1993']['outflw1']]
                v93 = [data['1993']['outflw1'][k]['v'].loc[index93] for k in data['1993']['outflw1']]
                quiv93.set_UVC(u93, v93)
            if index95 in data['1995']['outflw1'][str(cn[0])].index:
                u95 = [data['1995']['outflw1'][k]['u'].loc[index95] for k in data['1995']['outflw1']]
                v95 = [data['1995']['outflw1'][k]['v'].loc[index95] for k in data['1995']['outflw1']]
                quiv95.set_UVC(u95, v95)
            if index97 in data['1997']['outflw1'][str(cn[0])].index:
                u97 = [data['1997']['outflw1'][k]['u'].loc[index97] for k in data['1997']['outflw1']]
                v97 = [data['1997']['outflw1'][k]['v'].loc[index97] for k in data['1997']['outflw1']]
                quiv97.set_UVC(u97, v97)
            if index07 in data['2007']['outflw1'][str(cn[0])].index:
                u07 = [data['2007']['outflw1'][k]['u'].loc[index07] for k in data['2007']['outflw1']]
                v07 = [data['2007']['outflw1'][k]['v'].loc[index07] for k in data['2007']['outflw1']]
                quiv07.set_UVC(u07, v07)
            if index09 in data['2009']['outflw1'][str(cn[0])].index:
                u09 = [data['2009']['outflw1'][k]['u'].loc[index09] for k in data['2009']['outflw1']]
                v09 = [data['2009']['outflw1'][k]['v'].loc[index09] for k in data['2009']['outflw1']]
                quiv09.set_UVC(u09, v09)
            if index11 in data['2011']['outflw1'][str(cn[0])].index:
                u11 = [data['2011']['outflw1'][k]['u'].loc[index11] for k in data['2011']['outflw1']]
                v11 = [data['2011']['outflw1'][k]['v'].loc[index11] for k in data['2011']['outflw1']]
                quiv11.set_UVC(u11, v11)
            
            global contf93, contf95, contf97, contf07, contf09, contf11
            if index93 in data['1993']['avesalD'].index:
                sal93 = np.array(data['1993']['avesalD'].loc[index93])
                sali93 = griddata(lon, lat, sal93, loni, lati, interp='linear')
                sali93.mask = ~mask
                for c in contf93.collections: c.remove()
                contf93 = ax93.contourf(loni, lati, sali93, 50, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, alpha=.7)
            if index95 in data['1995']['avesalD'].index:
                sal95 = np.array(data['1995']['avesalD'].loc[index95])
                sali95 = griddata(lon, lat, sal95, loni, lati, interp='linear')
                sali95.mask = ~mask
                for c in contf95.collections: c.remove()
                contf95 = ax95.contourf(loni, lati, sali95, 50, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, alpha=.7)
            if index97 in data['1997']['avesalD'].index:
                sal97 = np.array(data['1997']['avesalD'].loc[index97])
                sali97 = griddata(lon, lat, sal97, loni, lati, interp='linear')
                sali97.mask = ~mask
                for c in contf97.collections: c.remove()
                contf97 = ax97.contourf(loni, lati, sali97, 50, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, alpha=.7)
            if index07 in data['2007']['avesalD'].index:
                sal07 = np.array(data['2007']['avesalD'].loc[index07])
                sali07 = griddata(lon, lat, sal07, loni, lati, interp='linear')
                sali07.mask = ~mask
                for c in contf07.collections: c.remove()
                contf07 = ax07.contourf(loni, lati, sali07, 50, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, alpha=.7)
            if index09 in data['2009']['avesalD'].index:
                sal09 = np.array(data['2009']['avesalD'].loc[index09])
                sali09 = griddata(lon, lat, sal09, loni, lati, interp='linear')
                sali09.mask = ~mask
                for c in contf09.collections: c.remove()
                contf09 = ax09.contourf(loni, lati, sali09, 50, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, alpha=.7)
            if index11 in data['2011']['avesalD'].index:
                sal11 = np.array(data['2011']['avesalD'].loc[index11])
                sali11 = griddata(lon, lat, sal11, loni, lati, interp='linear')
                sali11.mask = ~mask
                for c in contf11.collections: c.remove()
                contf11 = ax11.contourf(loni, lati, sali11, 50, zorder=0, cmap=plt.cm.seismic, vmin=0, vmax=30, alpha=.7)
            
            time_text93.set_text(index93)
            time_text95.set_text(index95)
            time_text97.set_text(index97)
            time_text07.set_text(index07)
            time_text09.set_text(index09)
            time_text11.set_text(index11)
            sys.stdout.write('\r{0} of 1345 frames'.format(i))
            
        anim = FuncAnimation(fig, update, frames=1345)
        
        plt.rcParams['animation.ffmpeg_path'] = 'C:\\ffmpeg\\bin\\ffmpeg.exe'
        writer = animation.FFMpegFileWriter(bitrate=1200, fps=7)
        string = r'T:\baysestuaries\USERS\TSansom\Projects\TNC_PTrac\ptrac_{0}_{1}.mp4'.format(cb,month)
        anim.save(string,writer=writer)
        plt.close()