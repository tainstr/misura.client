#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Parse CDV binary files"""
import struct
import re
from collections import OrderedDict


temptimes_v2_def = [('f', 'Version'),
('f', 'data_baseline'),
('f', 'thickness'),
('f', 't_half'),
('f', 'time_max_temp'),
('f', 'max_temp'),
('f', 'time_10_t_half'),
('f', 'temp_10_t_half'),
('f', 'furnace_temp'),
('f', 'cte'),
('8i', 'frac_times'),
('16i', 'frac_times_x'),
('12I', 'frac_times_y'),
('16i', 'frac_temps_x'),
('12f', 'frac_temps_y'),
('f', 'diffusivity'),
('f', 'heat_loss_diffusivity'),
('f', 'wo_heat_loss_diffusivity'),
('f', 'corrected_diffusivity'),
('f', 'uncorrected_diffusivity'),
('500f', '_values'),
('50l', 'values32'),
('I', 'pulse_time'),
('I', 'pulse_width'),
('f', 'sampling_rate'),
('i', 'repeat'),
('i', 'segment'),
('i', 'sample'),
('i', 'test'),
('f', 'baseline_slope'),
('f', 'baseline_b'),
('Q', 'eval_time'),
('I', 'eval_time2'),
('24c', 'codes'),
('i', 'num_error_codes'),
('f', 'fpc'),
('f', 'TC_fpc'),
('f', 'heckman_fpc'),
('f', 'azumi_fpc')]

temptimes_v2 = '<' +' '.join([el[0] for el in temptimes_v2_def])

values_def = (('c_software_version', 11),

('calc_parker', 0),
('calc_koski', 1),
('calc_heckman', 2),
('calc_center_gravity', 3),
('calc_cowan_5', 4),
('calc_cowan_10', 5),
('calc_clark_and_taylor_r1', 6),
('calc_clark_and_taylor_r2', 7),
('calc_clark_and_taylor_r3', 8),
('calc_degiovanni', 9),
('calc_in_plane_method', 12),
('calc_taylor_clark_fpc', 13),
('uncorrected_thickness', 14),
('calc_dtl_acq_gain', 15),
('calc_degiovanni_2_3', 16),
('calc_degiovanni_1_2', 17),
('calc_degiovanni_1_3', 18),

('degiovanni_5_6_time', 19),

('calc_conductivity', 21),
('calc_clark_and_taylor_avg', 22),
('calc_cowan_5_10_avg', 23),
('calc_specific_heat', 25),
('calc_method_tony', 26),

('da_volts_out', 20),
('sensor_offset', 24),
('laser_max_voltage', 27),
('laser_voltage_reading', 28),
('laser_voltage_setpoint', 29),
('system_furnace_type', 30),
('system_high_pressure', 31),
('system_iris', 32),
('system_carousel', 33),
('acq_switch_time', 34),
('acq_rate', 35),
('vacuum_reading_cdv', 40),

('calc_2_layer', 37),
('calc_2_layer_hc', 38),
('calc_3_layer', 39),
('calc_noise_type', 41),
('calc_noise_value', 42),
('calc_stddev_value', 43),
('calc_stddev_baseline_type', 44),
('calc_stddev_baseline_pre', 45),
('calc_stddev_baseline_pre_lr', 46),
('calc_stddev_baseline_post', 47),
('calc_stddev_signal_noise_ratio', 48),
('calc_stddev_baseline_post_2d', 49),
('calc_stddev_signal_noise_ratio_2d', 50),

('mat_used_cp_specificheat_value', 51),
('mat_used_cp_denisty_value', 52),
('mat_used_cp_diffusivity_value', 53),
('mat_calc_cp_conductivity_value', 54),
('mat_used_cp_maximum_value', 55),
('mat_used_cp_coeff_simul_max_dimless', 56),
('mat_used_cp_da_offset', 57),
('mat_used_cp_diameter', 58),
('mat_used_cp_thickness', 59),
('mat_used_cp_sensor', 60),
('mat_ref_cp_specificheat_value', 61),
('mat_ref_cp_denisty_value', 62),
('mat_ref_cp_diffusivity_value', 63),
('mat_ref_cp_maximum_value', 65),
('mat_ref_cp_coeff_simul_max_dimless', 66),
('mat_ref_cp_da_offset', 67),
('mat_ref_cp_diameter', 68),
('mat_ref_cp_thickness', 69),
('mat_ref_cp_sensor', 70),
('mat_used_cp_coeff_simul_max_dimless_org', 71),
('mat_center_gravity', 81),

('ee_max_temp', 73),
('ee_max_temp2', 74),
('cp_uncorrected', 75),
('cp_detector_sample_corr', 76),
('baseline_orig_s', 77),
('baseline_orig_b', 78),
('baseline_10_s', 79),
('baseline_10_b', 80),

('koski_a73', 83),
('koski_l73', 84),
('koski_a82', 85),
('koski_l82', 86),
('koski_a84', 87),
('koski_l84', 88),
('koski_a5', 89),
('koski_l5', 90),
('koski_r1', 91),
('koski_r2_73', 92),
('koski_r2_82', 93),
('koski_r2_84', 94),
('koski_r2_5', 95),
('koski_avg', 96),
('koski_maxloss', 97),
('koski_avg_use', 98),
('koski_value_used', 99),

('mat_parker_diff_ver_a', 101),
('mat_parker_goodness_ver_a', 102),
('mat_parker_ssr_ver_a', 103),
('mat_degio_diff_ver_a', 104),
('mat_degio_goodness_ver_a', 105),
('mat_degio_ssr_ver_a', 106),
('mat_moment_diff_ver_a', 107),
('mat_moment_goodness_ver_a', 108),
('mat_moment_ssr_ver_a', 109),
('mat_clarktaylor_diff_ver_a', 110),
('mat_clarktaylor_goodness_ver_a', 111),
('mat_clarktaylor_ssr_ver_a', 112),
('mat_log_diff_ver_a', 113),
('mat_log_goodness_ver_a', 114),
('mat_log_ssr_ver_a', 115),
('mat_nonlinear1p_diff_ver_a', 116),
('mat_nonlinear1p_goodness_ver_a', 117),
('mat_nonlinear1p_ssr_ver_a', 118),
('mat_nonlinear2p_diff_ver_a', 191),
('mat_nonlinear2p_goodness_ver_a', 192),
('mat_nonlinear2p_ssr_ver_a', 193),
('mat_half_time', 119),
('mat_small_diameter_diff', 121),
('mat_small_diameter_goodness', 122),
('mat_small_diameter_ssr', 123),
('mat_small_diameter_ir_ratio', 124),
('mat_small_diameter_mr_ratio', 125),
('mat_santa_diff', 127),
('mat_santa_ir_ratio', 128),
('mat_santa_mr_ratio', 129),
('mat_santa_detector_type', 130),
('mat_parker_diff', 131),
('mat_parker_goodness', 132),
('mat_parker_ssr', 133),
('mat_degio_diff', 134),
('mat_degio_goodness', 135),
('mat_degio_ssr', 136),
('mat_moment_diff', 137),
('mat_moment_goodness', 138),
('mat_moment_ssr', 139),
('mat_moment_diff_1d', 140),
('mat_moment_goodness_1d', 141),
('mat_moment_ssr_1d', 142),
('mat_clarktaylor_diff', 143),
('mat_clarktaylor_goodness', 144),
('mat_clarktaylor_ssr', 145),
('mat_log_diff', 146),
('mat_log_goodness', 147),
('mat_log_ssr', 148),
('mat_nonlinear1p_diff', 149),
('mat_nonlinear1p_goodness', 150),
('mat_nonlinear1p_ssr', 151),
('mat_nonlinear2p_diff', 152),
('mat_nonlinear2p_goodness', 153),
('mat_nonlinear2p_ssr', 154),

('shape_analysis_orig_ct', 159),
('shape_analysis_coeff0', 160),
('shape_analysis_coeff1', 161),
('shape_analysis_coeff2', 162),
('shape_analysis_coeff3', 163),
('shape_analysis_coeff4', 164),
('shape_analysis_coeff5', 165),
('shape_analysis_multi', 166),

('fast_laser_read_avg', 170),
('fast_laser_read_1', 171),
('fast_laser_read_2', 172),
('fast_laser_read_3', 173),
('fast_laser_read_4', 174),
('fast_laser_read_5', 175),
('fast_laser_read_std', 176),
('cp_laser_power_sample_orig', 177),
('cp_laser_power_sample_cpv', 178),
('cp_laser_power_sample_corr', 179),

('mat_partial_time_1', 181),
('mat_partial_time_2', 182),
('mat_partial_time_3', 183),
('mat_partial_time_4', 184),
('mat_partial_time_5', 185),
('mat_partial_time_6', 186),
('mat_partial_time_7', 187),
('mat_partial_time_8', 188),
('mat_partial_time_9', 189),
('mat_partial_time_10', 190),

('santa_new_num_iter', 194),
('santa_new_lsq_diff', 195),
('santa_new_biot', 196),
('santa_new_ndata', 197),
('santa_new_stopindex', 198),
('santa_new_gdf', 199),
('santa_new_ssr', 200),

('cdv_weight', 201),
('cdv_diameter', 202),
('filter_type', 204),
('filter_cut', 205),
('filter_bandwidth', 206),
('num_avg_points', 207),
('trg_type', 208),
('trg_pre', 209),
('trg_post', 210),
('detector_analysis_type', 211),
('cool_down_r_fit_type', 212),
('cool_down_r', 213),

('mat_moment1', 215),
('mat_parker_biot', 216),
('mat_degio_biot', 217),
('mat_moment_biot', 218),
('mat_moment_biot_1d', 219),
('mat_clarktaylor_biot', 220),
('mat_log_biot', 221),
('mat_log_2d_biot', 222),
('mat_nonlinear1p_biot', 223),
('mat_nonlinear2p_biot', 224),
('model_filtered_sfit_ct', 226),
('model_filtered_sfit_dg', 227),
('model_filtered_sfit_moment', 228),
('model_filtered_sfit_log', 229),
('model_filtered_sfit_lsq2d', 230),
('calc_baseline_slope', 233),
('calc_baseline_b', 234),
('calc_baseline_start', 235),
('calc_baseline_end', 236),
('mat_baseline', 237),
('mat_baseline_start', 238),
('mat_baseline_end', 239),
('calc_baseline_after', 240),
('calc_baseline_after_start', 241),
('calc_baseline_after_end', 242),
('multilayer_type', 243),
('capsule_type', 244),
('multilayer_thick_1', 245),
('multilayer_thick_2', 246),
('multilayer_thick_3', 247),
('calc_baseline_before_after_shift', 248),
('calc_baseline_before', 249),
('calc_baseline_before_start', 250),
('calc_baseline_before_end', 251),
('calc_max_temp_index', 279),
('calc_after_max_slope', 280),
('calc_after_max_angle', 281),
('calc_after_max_min_points_in_time', 282),
('calc_after_max_min_value', 283),
('calc_after_max_angle_1', 284),
('calc_after_max_angle_2', 285),
('calc_after_max_angle_3', 286),
('calc_after_max_angle_4', 287),
('calc_after_max_angle_5', 288),
('calc_after_max_angle_6', 289),
('calc_after_max_angle_7', 290),
('calc_after_max_angle_8', 291),
('calc_after_max_angle_9', 292),
('calc_after_max_angle_points', 293),

('lma_calcdiffusivitytype', 300),
('lma_diffusivity', 301),
('lma_maxrisetemptheoretical', 302),
('lma_baseline', 303),
('lma_slope', 304),
('lma_biot', 305),
('lma_thickness', 306),
('lma_radius', 307),
('lma_estbaseline', 308),
('lma_estslope', 309),
('lma_estbiot', 310),
('lma_estdiffusivity', 311),
('lma_esttempempxrise', 312),
('lma_pulseduration', 313),
('lma_irradiatedradiusinner', 314),
('lma_irradiatedradiusouter', 315),
('lma_viewedradius', 316),
('lma_startpoint', 317),
('lma_decimate', 318),
('lma_numpoints', 319),
('lma_chi_square', 320),
('lma_npar', 321),
('lma_nfree', 322),
('lma_npegged', 323),
('lma_niter', 324),
('lma_nfev', 325),
('lma_outerradiusmulti', 326),
('lma_innerradiusmulti', 327),
('lma_analysisseconds', 328),
('lma_numberroots', 329),
('lma_datafiletype', 330),
('lma_timeendmethod', 331),
('lma_timeend', 332),
('lma_diffusivity_error', 333),
('lma_maxrisetemptheoretical_error', 334),
('lma_baseline_error', 335),
('lma_slope_error', 336),
('lma_biot_error', 337),
('lma_status_error', 338),
('lma_2d_shift', 339),

('lma_ml_type', 340),
('lma_ml_diff', 341),
('lma_ml_biot', 342),
('lma_ml_l1_thk', 343),
('lma_ml_l1_diff', 344),
('lma_ml_l1_cp', 345),
('lma_ml_l1_dens', 346),
('lma_ml_l2_thk', 347),
('lma_ml_l2_diff', 348),
('lma_ml_l2_cp', 349),
('lma_ml_l2_dens', 350),
('lma_ml_l3_thk', 351),
('lma_ml_l3_diff', 352),
('lma_ml_l3_cp', 353),
('lma_ml_l3_dens', 354),
('lma_ml_radius', 355),
('lma_ml_temperature', 356),
('lma_ml_baseline', 357),
('lma_ml_deltatmax', 358),
('lma_ml_slope', 359),
('lma_ml_heatloss_1', 360),
('lma_ml_heatloss_2', 361),
('lma_ml_heatloss_3', 362),
('lma_ml_number_roots', 363),
('lma_ml_iexp', 364),
('lma_ml_thermal_contact_resis', 365),
('lma_ml_dimensionless_contact_r', 366),
('lma_ml_biot_1', 367),
('lma_ml_biot_2', 368),
('lma_ml_biot_3', 369),
('lma_ml_number_points', 370),
('lma_ml_decimate_number', 371),
('lma_ml_status_error', 372),
('lma_analysis_type', 373),
('lma_analysis_sub_type', 374),
('lma_2d_jump', 375),
('lma_2d_pulse_duration', 376),
('lma_2d_baseline', 377),
('lma_2d_slope', 383),
('lma_2d_iri', 378),
('lma_2d_iro', 379),
('lma_2d_vri', 380),
('lma_2d_vro', 381),
('lma_2d_analysis_error', 382),
('lma_ml_hc_diff', 387),
('lma_3l_diff', 388),

('jg_in_plane_type', 390),
('jg_in_plane_diff', 391),
('jg_in_plane_maxrisetemptheoretical', 392),
('jg_in_plane_baseline', 393),
('jg_in_plane_slope', 394),
('jg_in_plane_biot', 395),
('jg_in_plane_estbaseline', 396),
('jg_in_plane_estslope', 397),
('jg_in_plane_estbiot', 398),
('jg_in_plane_estdiffusivity', 399),
('jg_in_plane_esttempempxrise', 400),
('jg_in_plane_baseline_orig', 401),
('jg_in_plane_slope_orig', 402),
('jg_in_plane_baseline_shift', 403),
('jg_in_plane_calc_chisquare', 404),
('jg_in_plane_calc_diff_plusminus', 405),
('jg_in_plane_calc_tmax_plusminus', 406),
('jg_in_plane_diameter_1', 407),
('jg_in_plane_diameter_2', 408),
('jg_in_plane_diameter_3', 409),
('jg_in_plane_starttime', 410),
('jg_in_plane_endtime', 411),

('values_32_carousel_config_type', 40),
('values_32_carousel_cart_type', 41),
('values_32_carousel_number_positions', 42),
('values_32_filter_1', 43),
('values_32_filter_2', 44),
('values_32_high_low_gain', 45),
('values_32_mcc_sn_1', 46),
('values_32_mcc_sn_2', 47),
('values_32_mcc_sn_3', 48),
('values_32_skip_specimen', 49),

('capsule_type_none', 0),
('capsule_type_paste', 1),
('capsule_type_liquid', 2),
('capsule_type_powder', 3),
('capsule_type_inplane_1', 11),
('capsule_type_inplane_2', 12),
('capsule_type_inplane_3', 13),
('capsule_type_inplane_4', 14),
('capsule_type_inplane_5', 14),
('capsule_type_inplane_6', 14),

('multilayer_type_none', 0),
('multilayer_type_2_layer', 1),
('multilayer_type_2_layer_hc', 2),
('multilayer_type_3_layer', 3),
('multilayer_type_2_layer_mat', 11),
('multilayer_type_2_layer_hc_mat', 12),
('multilayer_type_3_layer_mat', 13))



class CDV(object):
    definition = temptimes_v2_def
    
    def __init__(self, data=False):
        self._values=None
        self.values=OrderedDict()
        if data:
            self.load(data)
        else:
            for typ, k in temptimes_v2_def:
                setattr(self, k, 0)
        
    def load(self, data):
        self.data=struct.unpack(temptimes_v2, data)
        i = 0
        for typ, name in temptimes_v2_def:
            n=re.sub("[^0-9]", "", typ)
            if not len(n):
                n = 1
                val = self.data[i]
            else:
                n = int(n)
                val = self.data[i:i+n]
            setattr(self, name, val)
            i+=n
        # Define values dictionary
        if self._values is not None:
            for k, v in values_def:
                self.values[k] = self._values[v]
            
    @classmethod
    def open(cls, path):
        data = open(path, 'rb').read()
        if not len(data)>5:
            data = False
        return cls(data) 
   
    def table(self):
        s=''
        for typ, name in temptimes_v2_def:
            val = getattr(self, name)
            if hasattr(val, '__getitem__'):
                continue
            s+='{}; {}\n'.format(name, val)
        for k, v in self.values.iteritems():
            s+='{}; {}\n'.format(k,v)
        return s
    
class GenericKeyValueResultFile(object):
    seps = (':', '=')
    def __init__(self, data=False):
        if data:
            self.load(data)
            
    def parse(self, line):
        key = line.pop(0).replace(' ', '').replace('-', '_')
        if len(key)<3:
            return False
        value = line.pop(0).split(' ')
        value = filter(lambda c: c!='', value)
        other = None
        if len(value)>1:
            other = value[1:]
        value = float(value[0])
        setattr(self, key, value)
        setattr(self, key+'_other', other)
        return True
    
    def load(self, data):
        while '  ' in data:
            data = data.replace('  ', ' ')
        for line in data.splitlines():
            if len(line)<4:
                continue
            valid = 0
            for sep in self.seps:
                if sep in line:
                    line = line.split(sep)
                    valid = 1
                    break
            if not valid:
                continue
            self.parse(line)
            
    
    @classmethod
    def open(cls, path):
        data = open(path, 'r').read()
        if not len(data)>50:
            return False
        return GenericKeyValueResultFile(data)
    
    def __getitem__(self, *k):
        return getattr(self, *k)
        

