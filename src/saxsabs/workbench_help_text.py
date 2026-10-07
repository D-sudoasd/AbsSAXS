"""Short bilingual help for the desktop workbench.

Each pair contains English followed by Chinese. Keep option tokens identical to
the workbench values; translating a displayed label must not change its meaning.
These strings describe existing behavior and do not enable disabled controls.
"""

_HELP_PAIRS = {
    "help_copy_tooltip": (
        "Copy the complete help text to the clipboard for sharing or saving.",
        "把完整帮助复制到剪贴板，便于分享或保存。",
    ),
    "hint_prefix": ("Note", "说明"),
    "hint_t1_files": (
        "Use a standard with known scattering intensity. Its background, dark image "
        "and detector settings must match the measurement.",
        "选择散射强度已知的标准样；背景、暗场及探测器距离、束心、波长等设置须与测量相符。",
    ),
    "hint_t1_phys": (
        "Time is exposure in seconds; I0 measures incident beam intensity; T is the fraction "
        "of incident light passing through the sample (0 < T ≤ 1).",
        "Time 是曝光秒数；I0 是入射光监测值；T 是穿过样品的光占入射光的比例（0 < T ≤ 1）。",
    ),
    "hint_t1_std_water": (
        "Water's reference intensity changes little with q, the coordinate corresponding "
        "to scattering angle. At 20 °C it is 0.01632 cm⁻¹; enter measured water temperature.",
        "水参考强度近似不随 q（对应散射角的位置坐标）变化；20 °C 时为 0.01632 cm⁻¹，请填实测水温。",
    ),
    "hint_t1_std_lupolen": (
        "Lupolen reference intensity depends on the batch. Load the curve for your standard.",
        "Lupolen 的参考强度与批次有关，请加载该标准样对应的参考曲线。",
    ),
    "hint_t2_global": (
        "K converts instrument readings to intensity with physical units for comparison "
        "across measurements. Its calibration record and correction settings must match.",
        "K 是把仪器读数换成带实际单位、可与其他测量比较的强度的倍数；其标定记录和校正设置须一致。",
    ),
    "hint_t2_thickness": (
        "Enter fixed thickness in mm; each frame still uses its own T. Automatic thickness "
        "is disabled because changes in T need not mean changes in thickness.",
        "填写固定厚度（mm），原位测量也用此值；每帧仍按透过比例校正。透过光的变化不一定代表厚度变化，自动厚度已禁用。",
    ),
    "hint_t2_integration": (
        "Full-ring and sector modes plot intensity against q, the coordinate corresponding "
        "to scattering angle; texture plots intensity against direction. Modes can be combined.",
        "全环和扇区输出强度随 q（对应散射角的位置坐标）的曲线；织构输出强度随方向的曲线，可同时选择。",
    ),
    "hint_t2_correction": (
        "Match calibration settings. A mask excludes pixels; flat field corrects pixels "
        "that read differently under the same light; the error model estimates error size.",
        "校正设置须与标定一致。掩膜排除像素，平场修正像素对相同光强读数不同的问题，误差模型估计误差大小。",
    ),
    "hint_t2_execution": (
        "Choose background/dark images and run Dry Check. Resume based only on file existence "
        "is disabled; corrected 2D packages separately verify source settings and file contents.",
        "选择背景与暗场后先预检查。仅按文件存在判断的续跑已禁用；校正二维包另行核对来源设置和文件内容。",
    ),
    "hint_t2_queue": (
        "Add sample images, then Dry Check their exposure, beam monitor, transmission, "
        "thickness and calibration record before running.",
        "添加样品图像后先预检查曝光、入射光监测值、透过率、厚度和标定记录，再运行。",
    ),
    "hint_t3_global": (
        "Use reduced relative 1D data: curves already background-subtracted and adjusted for "
        "exposure and "
        "beam strength. Raw-count correction is disabled; a current calibration is required.",
        "使用已扣背景、已换算到相同曝光与入射光强条件的相对一维数据；原始计数校正已禁用，须有有效标定。",
    ),
    "hint_t3_execution": (
        "Run Dry Check before conversion. Exists-only resume is disabled because it cannot "
        "verify that existing results match the current inputs and settings.",
        "转换前先预检查。仅按文件存在判断的续跑无法验证结果是否对应当前输入和设置，已禁用。",
    ),
    "hint_t3_raw": (
        "These legacy raw-1D controls are disabled. Dark exposure and blank subtraction "
        "must first use the validated 2D correction procedure.",
        "这些旧版原始一维控件已禁用；暗场曝光匹配和空白扣除须先统一到已验证的二维校正流程。",
    ),
    "hint_t3_queue": (
        "Dry Check verifies each profile's columns, axis units, relative intensity state "
        "and calibration source before conversion.",
        "预检查逐条核对曲线列、坐标单位、相对强度状态和标定来源，再进行转换。",
    ),
    "hint_t3_alpha_uncertainty": (
        "Standard uncertainty estimates error size. Leave buffer multiplier α's uncertainty "
        "blank if unknown; the combined estimate stays NaN (missing), never zero.",
        "标准不确定度用于估计误差大小。缓冲液倍数 α 的该数值未知时留空；合成值保留为缺失（NaN），不设为零。",
    ),
    "hint_t3_fluo": (
        "Fluorescence is subtracted after conversion to intensity in cm⁻¹ and optional "
        "buffer subtraction. "
        "A high-q estimate requires negligible sample scattering in that window.",
        "先换成带实际单位的强度并按需扣缓冲液，再扣荧光；高 q 区间估计只适用于该区间样品散射可忽略的情况。",
    ),
    "tip_browse_file": ("Open the file picker and fill this path.", "打开文件选择窗口并填写此路径。"),
    "tip_browse_dir": (
        "Open the folder picker and fill this directory path.",
        "打开文件夹选择窗口并填写此目录路径。",
    ),
    "tip_output_format": (
        "Choose how curves are saved. canSAS XML and NXcanSAS HDF5 require Q (Å⁻¹), "
        "the coordinate derived from scattering angle; "
        "direction-angle curves cannot use them.",
        "选择曲线保存格式。canSAS XML 和 NXcanSAS HDF5 要求 q 轴为 Å⁻¹，不能用于方位角曲线。",
    ),
    "tip_plot_preset": (
        "Choose figure size, resolution, text size and line width for the exported plot.",
        "选择导出图像的尺寸、分辨率、字号和线宽。",
    ),
    "tip_plot_format": (
        "PNG/TIFF save pixels; PDF/SVG/EPS save vector graphics that remain sharp when enlarged.",
        "PNG/TIFF 保存像素图；PDF/SVG/EPS 保存矢量图，放大后线条仍清晰。",
    ),
    "tip_plot_export": (
        "Save the current figure with the selected preset and format, including its labels.",
        "按所选预设和格式保存当前图像，并保留轴标签。",
    ),
    "tip_t1_guide": (
        "Follow the displayed steps to choose files, verify parameters and calculate K.",
        "按显示的步骤选择文件、核对参数并计算 K。",
    ),
    "tip_t1_std_entry": (
        "Select the measured image of a standard with known scattering intensity. "
        "It sets the multiplier that converts instrument readings to comparable intensity.",
        "选择散射强度已知的标准样图像。程序用它计算把仪器读数换成可比较强度的倍数。",
    ),
    "tip_t1_std_btn": ("Select the measured standard image.", "选择实测标准样图像。"),
    "tip_t1_bg_entry": (
        "The measured blank or empty-cell image used to subtract background scattering.",
        "用于扣除背景散射的空白或空样品池实测图像。",
    ),
    "tip_t1_bg_btn": ("Select the background image.", "选择背景图像。"),
    "tip_t1_bg_multi": (
        "Select repeated background images. Adjust them to the same exposure and beam "
        "conditions, then average them for subtraction.",
        "选择重复测量的背景图像；程序把读数换到相同曝光和入射光强条件，平均后用于扣除。",
    ),
    "tip_t1_dark_entry": (
        "Detector image recorded without the beam; removes electronic and dark-current signal.",
        "无光束时记录的探测器图像，用于扣除电子噪声和暗电流信号。",
    ),
    "tip_t1_dark_btn": ("Select the dark image.", "选择暗场图像。"),
    "tip_t1_poni_entry": (
        "The geometry file gives detector distance, beam centre and wavelength. It converts "
        "pixels to q, the coordinate corresponding to scattering angle.",
        "几何文件记录探测器距离、束心和波长，用于把像素位置换成对应散射角的坐标 q。",
    ),
    "tip_t1_poni_btn": ("Select the pyFAI .poni geometry file.", "选择 pyFAI 的 .poni 几何文件。"),
    "tip_t1_std_exp": (
        "Standard exposure duration in seconds. Verify the value read from the image header.",
        "标准样曝光时长（秒），请核对图像头信息读取的数值。",
    ),
    "tip_t1_std_i0": (
        "Incident beam monitor reading for the standard. Select rate or integrated counts "
        "according to the beamline's recorded quantity.",
        "标准样的入射光监测值；根据线站记录的是每秒计数还是曝光总计数选择下方模式。",
    ),
    "tip_t1_std_t": (
        "Standard transmission: the fraction of incident light passing through it. "
        "Enter a fraction above 0 and at most 1, not a percentage.",
        "标准样透过率：穿过标准样的光占入射光的比例。填写大于 0、不超过 1 的小数，不填百分数。",
    ),
    "tip_t1_std_thk": (
        "Beam path length through the standard in mm. SRM 3600 uses the certificate "
        "thickness and locks this field; other standards require an explicit value.",
        "光束穿过标准样的厚度（mm）。SRM 3600 使用证书厚度并锁定此项；其他标准须填写实际厚度。",
    ),
    "tip_t1_bg_exp": (
        "Background exposure duration in seconds; used to put background and sample "
        "readings on the same measurement conditions.",
        "背景图的曝光时长（秒）；用于把背景和样品读数换到相同测量条件。",
    ),
    "tip_t1_bg_i0": (
        "Background incident beam monitor reading. Its count convention must match the standard.",
        "背景测量的入射光监测值，计数模式须与标准样一致。",
    ),
    "tip_t1_bg_t": (
        "Fraction of incident light passing through the background measurement, "
        "with 0 < T ≤ 1; used to correct for attenuation.",
        "背景测量中透过的光占入射光的比例；填写 0 < T ≤ 1 的小数，用于修正光衰减。",
    ),
    "tip_t1_norm_mode": (
        "Choose rate for counts per second or integrated for total counts during exposure. "
        "This choice also applies to batch processing.",
        "每秒计数选 rate，整次曝光总计数选 integrated；此设置同时用于批处理。",
    ),
    "tip_t1_norm_hint": (
        "rate divides by exposure × I0 × T; integrated divides by I0 × T. "
        "The wrong mode counts exposure time incorrectly.",
        "rate 除以曝光时间 × I0 × T；integrated 除以 I0 × T。模式选错会错误地计入曝光时间。",
    ),
    "tip_t1_solid_angle": (
        "Correct for the different solid angles seen by detector pixels. Keep this setting "
        "the same in calibration and batch processing.",
        "修正各探测器像素对应的立体角差异；标定与批处理必须使用相同设置。",
    ),
    "tip_t1_calibrate": (
        "Subtract the background, integrate the image and compare it with the reference "
        "curve to calculate K and record its sources.",
        "扣背景并积分图像，与参考曲线比较后计算 K，同时记录标定来源。",
    ),
    "tip_t1_history": (
        "Open past K values to compare calibrations over time; check conditions before "
        "interpreting differences as instrument drift.",
        "打开历史 K 值比较各次标定；判断仪器漂移前须确认测量条件一致。",
    ),
    "tip_t1_report": (
        "Read K, the fitted q range, usable point count and spread of individual K estimates.",
        "查看 K、参与拟合的 q 范围、有效点数，以及各点算出的 K 相差多少。",
    ),
    "tip_t1_plot": (
        "Dashed line: signal after background subtraction; blue line: intensity converted "
        "using K; orange reference markers: the standard's known intensity. Compare blue "
        "and orange; matching shapes alone do not verify units or calibration sources.",
        "虚线是扣背景后的信号，蓝线是用 K 换算后的强度，橙色参考点是标准样的已知强度。"
        "比较蓝线和橙点是否接近；形状相符仍须核对单位与标定来源。",
    ),
    "tip_t2_guide": (
        "Set fixed thickness and integration modes, add images and run Dry Check "
        "before processing.",
        "设置固定厚度和积分方式，添加图像后先预检查，再处理。",
    ),
    "tip_t2_k_factor": (
        "Read-only multiplier from Tab 1 for converting readings to intensity with physical "
        "units. Its complete calibration record must match the current inputs and settings.",
        "第 1 页标定得到的只读换算倍数，用于换成带实际单位的强度；其完整标定记录须与当前输入和设置一致。",
    ),
    "tip_t2_bg_label": (
        "The shared background path from calibration; automatic matching may select a "
        "different background for each sample.",
        "显示标定页共享的背景路径；自动匹配时各样品可能使用不同背景。",
    ),
    "tip_t2_norm_mode": (
        "Choose rate for monitor counts per second or integrated for exposure-total counts. "
        "It is shared with calibration.",
        "监测值为每秒计数选 rate，为曝光总计数选 integrated；此设置与标定页共用。",
    ),
    "tip_t2_norm_hint": (
        "The divisor is exposure × I0 × T in rate mode and I0 × T in integrated mode.",
        "rate 模式除以曝光时间 × I0 × T；integrated 模式除以 I0 × T。",
    ),
    "tip_t2_auto_thk": (
        "Disabled for formal output. Estimating thickness from T and μ can mistake "
        "transmission drift for thickness changes in a constant-thickness sample.",
        "正式输出已禁用。用 T 和 μ 估计厚度可能把恒厚样品的透过率漂移误判为厚度变化。",
    ),
    "tip_t2_mu": (
        "Read-only estimate of attenuation μ in cm⁻¹: how strongly light weakens per "
        "unit path length. Fixed-thickness processing does not use this estimate.",
        "只读估计衰减系数 μ（cm⁻¹），表示单位路径长度的光减弱程度；固定厚度处理不使用此估计值。",
    ),
    "tip_t2_mu_est": (
        "Open a provenance-aware diagnostic calculator: it estimates how strongly the "
        "material weakens X-rays from composition and NIST 30 keV or xraydb/Elam data, "
        "and records the data sources.",
        "根据成分和 NIST 30 keV 或 xraydb/Elam 数据，估计材料使 X 射线减弱的程度，并记录来源。",
    ),
    "tip_t2_fix_thk": (
        "Use one entered thickness for the samples. Per-frame T normalization remains active: "
        "each image is still corrected for its measured fraction of transmitted light.",
        "样品使用填写的统一厚度；每帧仍按自己的透过率校正。",
    ),
    "tip_t2_fix_thk_val": (
        "Enter the positive beam path length through the samples in mm, not cm.",
        "填写光束穿过样品的厚度，须大于 0，单位为 mm，不是 cm。",
    ),
    "tip_t2_mu_label": (
        "μ is estimated from composition data, not measured on the sample. "
        "Enter measured thickness in the fixed-thickness field for formal output.",
        "μ 根据材料成分估计，不是样品实测值；正式输出请在固定厚度栏填写实测厚度。",
    ),
    "tip_t2_full": (
        "Average all usable directions around the beam to produce intensity versus q; "
        "appropriate when scattering is direction-independent.",
        "对束心周围全部可用方向平均，输出强度随 q 的曲线，适合散射不随方向变化的样品。",
    ),
    "tip_t2_sector": (
        "Integrate only selected directions to produce intensity versus q for each sector.",
        "只积分选定方向，输出各扇区的强度随 q 的曲线。",
    ),
    "tip_t2_sec_min": (
        "Sector start in degrees around the beam: 0° right, 90° down, −90° up. "
        "170° to −170° crosses the left direction.",
        "扇区起始角（度）：0° 向右，90° 向下，−90° 向上；170° 到 −170° 跨过左侧方向。",
    ),
    "tip_t2_sec_max": (
        "Sector end in degrees. Start and end must differ even after adding or subtracting 360°.",
        "扇区结束角（度）；起止角即使相差整圈 360° 也不能表示同一方向。",
    ),
    "tip_t2_sec_preview": (
        "Show the detector pixels included in the selected sectors or full ring. "
        "Requires a sample image and geometry file.",
        "显示扇区或全环实际包含的探测器像素；须先有样品图像和几何文件。",
    ),
    "tip_t2_sec_multi": (
        "Enter several start~end pairs in degrees, e.g. −25~25;45~65. Leave blank to "
        "use the single start/end pair above.",
        "填写多组起始角~结束角（度），如 −25~25;45~65；留空使用上方单组起止角。",
    ),
    "tip_t2_sec_each": (
        "Save a separate curve and subfolder for each sector.",
        "为每个扇区分别保存曲线，并使用各自的子文件夹。",
    ),
    "tip_t2_sec_sum": (
        "Save one combined curve using pixel weights across the selected sectors; "
        "it is not a simple sum of sector intensities.",
        "按像素权重合并所选扇区并保存一条曲线，不是把各扇区强度直接相加。",
    ),
    "tip_t2_texture": (
        "Within the chosen q band, plot intensity versus angle around the beam to examine "
        "directional scattering.",
        "在选定 q 环带内输出强度随束心周围角度的曲线，用于观察散射的方向分布。",
    ),
    "tip_t2_qmin": (
        "Lower edge of the texture q band in Å⁻¹. q locates scattering by angle and wavelength.",
        "织构 q 环带的下限（Å⁻¹）；q 根据散射角和波长确定散射位置。",
    ),
    "tip_t2_qmax": (
        "Upper edge of the texture q band in Å⁻¹; must exceed the lower edge.",
        "织构 q 环带的上限（Å⁻¹），须大于下限。",
    ),
    "tip_t2_chi_preview": (
        "Show the detector ring between the chosen q limits; requires a sample image "
        "and geometry file.",
        "显示所选 q 上下限之间的探测器环带；须先有样品图像和几何文件。",
    ),
    "tip_t2_solid_angle": (
        "Correct pixel solid angles. A different choice from calibration blocks processing "
        "because the same K would no longer apply.",
        "修正像素立体角；与标定设置不同会阻止处理，因为原有 K 不再适用。",
    ),
    "tip_t2_error_model": (
        "Choose how to estimate error size: azimuthal uses ring intensity differences; "
        "poisson uses count statistics; none provides no estimate.",
        "选择误差大小的估计方法：azimuthal 用环内强度差异，poisson 用计数统计，none 不提供估计。",
    ),
    "tip_t2_polarization": (
        "Correct the beam's polarization only with a known factor from −1 to 1. "
        "The numeric field is inactive when this correction is off.",
        "已知光束偏振因子（−1 到 1）时才启用校正；关闭校正时数值栏不参与计算。",
    ),
    "tip_t2_mask": (
        "Optional image marking excluded detector pixels: nonzero means excluded. "
        "Its dimensions must match the sample image.",
        "可选像素排除图：非零像素不参与计算；图像尺寸须与样品一致。",
    ),
    "tip_t2_flat": (
        "Optional flat-field image correcting pixels that read differently under the same light; "
        "its dimensions must match the sample image.",
        "可选平场图，用于修正像素在相同光强下读数不同的问题；图像尺寸须与样品一致。",
    ),
    "tip_t2_ref_fixed": (
        "Use the background and dark images selected on the calibration page for every sample.",
        "所有样品都使用标定页选定的背景和暗场图像。",
    ),
    "tip_t2_ref_auto": (
        "Match background and dark images from the libraries by acquisition metadata; "
        "matching does not remove geometry or exposure checks.",
        "按采集元数据从文件库匹配背景和暗场；匹配后仍须通过几何与曝光校验。",
    ),
    "tip_t2_bg_lib": ("Add background candidates for automatic matching.", "添加自动匹配用的背景候选图像。"),
    "tip_t2_dark_lib": ("Add dark-image candidates for automatic matching.", "添加自动匹配用的暗场候选图像。"),
    "tip_t2_bg_lib_folder": (
        "Add background candidates from this folder and its subfolders.",
        "添加此文件夹及子文件夹中的背景候选图像。",
    ),
    "tip_t2_dark_lib_folder": (
        "Add dark-image candidates from this folder and its subfolders.",
        "添加此文件夹及子文件夹中的暗场候选图像。",
    ),
    "tip_t2_clear_lib": (
        "Remove background/dark candidates from the libraries; disk files remain.",
        "移除文件库中的背景和暗场候选项，磁盘文件保留。",
    ),
    "tip_t2_workers": (
        "Number of processing threads; 1 processes files sequentially. More threads "
        "use more memory and do not always run faster.",
        "处理线程数；1 表示逐个处理。更多线程占用更多内存，不一定更快。",
    ),
    "tip_t2_resume": (
        "Disabled: ordinary 1D results were skipped solely because files existed, "
        "without checking inputs, settings or contents. Calibrated 2D has separate checks.",
        "已禁用：普通一维结果原来只因文件存在就跳过，未核对输入、设置和内容；校正二维包另有校验。",
    ),
    "tip_t2_overwrite": (
        "Recalculate and replace existing outputs at the target paths. "
        "Leave off to avoid replacing existing results.",
        "重新计算并替换目标路径已有的输出；关闭时避免替换现有结果。",
    ),
    "tip_t2_strict": (
        "Check energy, wavelength, detector distance, pixel size and image dimensions; "
        "inconsistent measurements cannot share one geometry.",
        "核对能量、波长、探测器距离、像素尺寸和图像尺寸；不一致的测量不能共用同一几何。",
    ),
    "tip_t2_tolerance": (
        "Allowed relative difference in instrument parameters, in percent; "
        "0.5 means 0.5%, not 50%.",
        "仪器参数允许的相对差异（%）；0.5 表示 0.5%，不是 50%。",
    ),
    "tip_t2_export_cal2d": (
        "Save the corrected detector image with geometry, mask and source metadata "
        "for later integration in pyFAI or pydidas.",
        "保存校正后的探测器图像及几何、掩膜、来源信息，供 pyFAI 或 pydidas 后续积分。",
    ),
    "tip_t2_cal2d_flat": (
        "Include flat-field correction in the saved 2D pixels. Do not apply flat field "
        "again when reintegrating this package.",
        "把平场校正写入保存的二维像素；重新积分此数据包时不要再次做平场校正。",
    ),
    "tip_t2_cal2d_dtype": (
        "Choose saved pixel precision: float32 uses less space; float64 retains "
        "more numerical digits, without improving measurement accuracy.",
        "选择像素保存精度：float32 占用空间较小，float64 保留更多数值位数，但不会提高测量准确度。",
    ),
    "tip_t2_add": (
        "Add one or more sample images (.tif, .tiff, .edf or .cbf) to the queue.",
        "把一个或多个样品图像（.tif、.tiff、.edf、.cbf）加入队列。",
    ),
    "tip_t2_add_folder": (
        "Add sample images from a folder and its subfolders to the queue.",
        "把文件夹及子文件夹中的样品图像加入队列。",
    ),
    "tip_t2_clear": ("Empty the sample queue; disk files remain.", "清空样品队列，磁盘文件保留。"),
    "tip_t2_check": (
        "Check image metadata, fixed thickness, geometry, calibration sources and "
        "enabled corrections; read the reported failures before running.",
        "检查图像元数据、固定厚度、几何、标定来源和已启用的校正；运行前先查看报告中的失败项。",
    ),
    "tip_t2_group": (
        "Group queued files by acquisition time and record group IDs in the manifest. "
        "This does not change output routing (where results are saved) or background/dark "
        "matching.",
        "按采集时间分组并在处理清单中记录组号；不会改变输出路由（保存位置）或背景、暗场匹配。",
    ),
    "tip_t2_listbox": (
        "Queued sample images. Select one to use it for the integration-region preview.",
        "待处理样品图像列表；选择一项可将其用于积分区域预览。",
    ),
    "tip_t2_run": (
        "Process the queue using current settings after a valid Dry Check. "
        "Individual file errors are recorded; other files continue.",
        "有效预检查后按当前设置处理队列；单个文件失败会记录错误，其余文件继续处理。",
    ),
    "tip_t2_progress": (
        "Shows processing progress; inspect the batch report to distinguish success, "
        "skips and failures.",
        "显示处理进度；请查看批处理报告区分成功、跳过和失败。",
    ),
    "tip_t2_outdir": (
        "Optional output root folder. Leave blank to save outputs beside each input "
        "in the mode's output subfolder.",
        "可选输出根目录；留空时在各输入文件旁的对应积分模式子目录中保存。",
    ),
    "tip_t2_out_label": (
        "Shows the output locations for the selected integration modes; batch reports "
        "record each file's outcome.",
        "显示所选积分方式的输出位置；批处理报告记录各文件的处理结果。",
    ),
    "tip_t2_fluo_method": (
        "Choose a constant, an estimate from a high-q window, or measured fluorescence. "
        "A high-q estimate is valid only when sample scattering there is negligible.",
        "选择常数、高 q 区间估计或实测荧光；只有该区间样品散射可忽略时，高 q 估计才适用。",
    ),
    "tip_t2_fluo_f0": (
        "Constant fluorescence intensity to subtract in cm⁻¹; required for constant mode.",
        "待扣除的常数荧光强度（cm⁻¹），constant 模式须填写。",
    ),
    "tip_t2_fluo_f0_uncertainty": (
        "Standard uncertainty estimates the error size of constant fluorescence, in cm⁻¹. "
        "Leave blank if unknown; missing does not mean zero.",
        "常数荧光强度的标准不确定度，即估计误差大小（cm⁻¹）；未知时留空，缺失不表示零。",
    ),
    "tip_t2_fluo_beta": (
        "Positive multiplier β applied to fluorescence before subtraction; 1 uses "
        "the fluorescence estimate unchanged.",
        "荧光扣除前乘以的倍数 β，须大于 0；1 表示使用原荧光估计值。",
    ),
    "tip_t2_fluo_beta_uncertainty": (
        "Standard uncertainty estimates the error size of fluorescence multiplier β; "
        "leave blank when unknown.",
        "荧光倍数 β 的标准不确定度，即估计误差大小；未知时留空。",
    ),
    "tip_t2_fluo_qmin": (
        "Lower q limit of the fluorescence estimation window in Å⁻¹; select a region "
        "where sample scattering is negligible.",
        "荧光估计区间的 q 下限（Å⁻¹）；须选择样品散射可忽略的区域。",
    ),
    "tip_t2_fluo_qmax": (
        "Upper q limit of the fluorescence estimation window in Å⁻¹; must exceed "
        "the lower limit.",
        "荧光估计区间的 q 上限（Å⁻¹），须大于下限。",
    ),
    "tip_t2_fluo_file": (
        "Measured fluorescence curve with a q axis and absolute intensity in cm⁻¹; "
        "relative or angle-axis data cannot be used directly.",
        "带 q 轴、绝对强度单位为 cm⁻¹ 的实测荧光曲线；不能直接使用相对强度或角度坐标数据。",
    ),
    "tip_t3_guide": (
        "Convert already reduced relative 1D profiles using a verified calibration. "
        "Raw-count correction is disabled.",
        "用已验证的标定转换已完成校正和归一化的相对强度一维曲线；原始计数校正已禁用。",
    ),
    "tip_t3_k": (
        "Read-only K from calibration. A positive number alone is insufficient; "
        "Dry Check must verify its source record.",
        "标定得到的只读 K；仅有正数还不够，预检查须验证其来源记录。",
    ),
    "tip_t3_k_factor": (
        "Read-only calibration multiplier; default values and old values without "
        "complete source records cannot produce formal output.",
        "只读标定换算倍数；默认值或缺少完整来源记录的旧值不能用于正式输出。",
    ),
    "tip_t3_scaled": (
        "Use profiles already background-subtracted and adjusted for exposure and beam "
        "strength, labelled relative. Convert to physical units without repeating corrections.",
        "使用已扣背景、已换到相同曝光和入射光强条件且标记为 relative 的曲线；只换成带实际单位的强度。",
    ),
    "tip_t3_raw": (
        "Disabled: legacy raw-count 1D correction does not share the validated 2D "
        "procedure. Supply a reduced relative curve or reintegrate a calibrated 2D package.",
        "已禁用：旧版原始计数一维校正未共用已验证的二维流程。请提供已校正相对曲线或重积分校正二维包。",
    ),
    "tip_t3_kd": (
        "Multiply by K and divide by thickness when the relative input has not already "
        "been divided by thickness. Thickness is entered in mm and converted internally.",
        "相对输入尚未除以厚度时，乘 K 后除以厚度；厚度填写 mm，程序内部换算单位。",
    ),
    "tip_t3_thk": (
        "Positive thickness in mm, used only for K/d scaling. Do not divide by "
        "thickness again if the input already includes it.",
        "正数厚度（mm），仅用于 K/d 换算；输入已除过厚度时不要再除一次。",
    ),
    "tip_t3_k_only": (
        "Multiply by K only when the relative input has already been divided by thickness.",
        "相对输入已经除以厚度时，仅乘以 K。",
    ),
    "tip_t3_x_mode": (
        "Choose the input axis: q is a scattering coordinate; 2θ is scattering angle; "
        "χ is direction around the beam. Auto requires explicit units; 2θ needs wavelength.",
        "选择输入坐标：q 是散射位置坐标，2θ 是散射角，χ 是束心周围方向角。auto 须有明确单位，2θ 须填波长。",
    ),
    "tip_t3_resume": (
        "Disabled: the legacy option checked only whether output files existed, "
        "not their contents or their input and processing sources.",
        "已禁用：旧选项只检查输出文件是否存在，未核对内容及其输入和处理来源。",
    ),
    "tip_t3_overwrite": (
        "Recalculate and replace existing target results. Verify the output directory "
        "before enabling this option.",
        "重新计算并替换目标位置已有的结果；启用前请确认输出目录。",
    ),
    "tip_t3_meta": (
        "Legacy raw-1D metadata input; disabled with raw correction. It does not replace "
        "the source information required by the active relative-profile workflow.",
        "旧版原始一维元数据输入，随原始校正禁用；不能替代当前相对曲线流程要求的来源信息。",
    ),
    "tip_t3_bg1d": (
        "Legacy raw-1D background curve; disabled with raw correction. Active scaled "
        "inputs must already have background subtraction recorded.",
        "旧版原始一维背景曲线，随原始校正禁用；当前相对输入须已扣背景并有记录。",
    ),
    "tip_t3_dark1d": (
        "Legacy raw-1D dark curve; disabled with raw correction. It is not applied "
        "again to reduced relative profiles.",
        "旧版原始一维暗场曲线，随原始校正禁用；不会再次应用到已校正的相对曲线。",
    ),
    "tip_t3_meta_from_batch": (
        "Legacy conversion of a batch report to raw-1D metadata; unavailable while "
        "the raw-1D panel is disabled.",
        "旧版批处理报告转原始一维元数据功能；原始一维面板禁用时不可使用。",
    ),
    "tip_t3_meta_thk": (
        "Legacy thickness override from metadata; disabled with raw correction. "
        "Use the active fixed-thickness field for K/d scaling.",
        "旧版元数据厚度覆盖选项，随原始校正禁用；K/d 换算使用当前固定厚度栏。",
    ),
    "tip_t3_sync_bg": (
        "Legacy synchronization of background parameters from calibration; disabled "
        "with the raw-1D panel.",
        "旧版从标定页同步背景参数的选项，随原始一维面板禁用。",
    ),
    "tip_t3_add": (
        "Add external relative 1D profiles. They need explicit axis units, correction "
        "state and source information.",
        "添加外部相对强度一维曲线；须有明确坐标单位、校正状态和来源信息。",
    ),
    "tip_t3_clear": ("Empty the 1D conversion queue; disk files remain.", "清空一维转换队列，磁盘文件保留。"),
    "tip_t3_check": (
        "Check columns, axis units, intensity state, correction history and calibration "
        "sources; changes to inputs or settings require another check.",
        "检查列、坐标单位、强度状态、校正记录和标定来源；输入或设置变化后须重新检查。",
    ),
    "tip_t3_listbox": ("Profiles queued for absolute scaling.", "等待换算绝对强度的曲线列表。"),
    "tip_t3_run": (
        "After a valid Dry Check, convert reduced relative profiles with K/d or K "
        "and save their correction and source records.",
        "有效预检查后，以 K/d 或 K 转换已校正相对曲线，并保存校正与来源记录。",
    ),
    "tip_t3_progress": (
        "Shows conversion progress; read the report for each profile's final outcome.",
        "显示转换进度；各曲线的最终结果请查看报告。",
    ),
    "tip_t3_outdir": (
        "Optional output directory. If blank, outputs go to the conversion subfolder "
        "beside the first input file.",
        "可选输出目录；留空时写入首个输入文件旁的转换结果子目录。",
    ),
    "tip_t3_fluo_beta_uncertainty": (
        "Standard uncertainty estimates the error size of fluorescence multiplier β; "
        "leave blank when unknown.",
        "荧光倍数 β 的标准不确定度，即估计误差大小；未知时留空。",
    ),
    "tip_t3_fluo_qmin": (
        "Lower q limit in Å⁻¹ for estimating fluorescence after absolute scaling; "
        "sample scattering in this window must be negligible.",
        "绝对强度换算后用于估计荧光的 q 下限（Å⁻¹）；此区间样品散射须可忽略。",
    ),
    "tip_t3_fluo_qmax": (
        "Upper q limit of the fluorescence estimation window in Å⁻¹; must exceed "
        "the lower limit.",
        "荧光估计区间的 q 上限（Å⁻¹），须大于下限。",
    ),
}

_EXTRA_PAIRS = {
    "tip_t1_std_type": (
        "Choose the measured standard. SRM 3600 uses its certificate; water uses "
        "temperature; Lupolen and custom standards need a reference file.",
        "选择实测标准样类型。SRM 3600 使用证书，水使用温度模型，Lupolen 和自定义标准须提供参考文件。",
    ),
    "tip_t1_water_temp": (
        "Measured water temperature in °C, from 4 to 40. It changes the reference "
        "intensity used for calibration.",
        "实测水温（°C），范围为 4 到 40；此温度决定标定所用的水参考强度。",
    ),
    "tip_t1_std_ref_file": (
        "Reference curve with known intensity in cm⁻¹ for Lupolen or a custom standard. "
        "Label q units "
        "explicitly as Å⁻¹, nm⁻¹ or m⁻¹; a 2θ or χ axis is not accepted.",
        "Lupolen 或自定义标准的已知强度曲线（cm⁻¹）；q 单位须明确为 Å⁻¹、nm⁻¹ 或 m⁻¹，不接受角度轴。",
    ),
    "tip_t1_qmin": (
        "Lower edge of the calibration fit in Å⁻¹; use only the overlap with the "
        "standard's valid reference range.",
        "标定拟合的 q 下限（Å⁻¹）；只使用测量与标准有效参考范围的重叠部分。",
    ),
    "tip_t1_qmax": (
        "Upper edge of the calibration fit in Å⁻¹; it must lie within the valid "
        "overlap and exceed the lower edge.",
        "标定拟合的 q 上限（Å⁻¹）；须处于有效重叠范围内并大于下限。",
    ),
    "tip_t2_buffer_enable": (
        "Multiply the background term by α before subtraction. This scales the selected "
        "2D background; it does not load a separate absolute buffer curve.",
        "扣除前把背景项乘以 α；此项缩放所选二维背景，不加载另一条绝对强度缓冲液曲线。",
    ),
    "tip_t2_alpha": (
        "Background multiplier α; 1 leaves the background unchanged. It is used only "
        "when background scaling is enabled.",
        "背景倍数 α；1 表示不改变背景，仅在启用背景缩放时使用。",
    ),
    "tip_t2_fluo_enable": (
        "Subtract an estimated or measured fluorescence contribution after absolute "
        "scaling; fill the fields for the selected method.",
        "绝对强度换算后扣除估计或实测的荧光贡献；须填写所选方法需要的参数。",
    ),
    "tip_t3_wavelength": (
        "X-ray wavelength in Å, required to convert scattering angle 2θ to its q coordinate. "
        "It is not needed for an input already labelled with q units.",
        "X 射线波长（Å），把散射角 2θ 换成位置坐标 q 时必填；已明确标记 q 单位的输入不需要此项。",
    ),
    "tip_t3_sample_exp": (
        "Legacy raw-1D sample exposure in seconds; disabled and unused by scaled conversion.",
        "旧版原始一维样品曝光时间（秒）；已禁用，当前相对强度换算不使用。",
    ),
    "tip_t3_sample_i0": (
        "Legacy raw-1D incident beam monitor reading; disabled and unused by scaled conversion.",
        "旧版原始一维入射光监测值；已禁用，当前相对强度换算不使用。",
    ),
    "tip_t3_sample_t": (
        "Legacy raw-1D transmission fraction (0 < T ≤ 1); disabled. "
        "Reduced input must already record its transmission correction.",
        "旧版原始一维透过率（0 < T ≤ 1）；已禁用，已校正输入须已有透过率校正记录。",
    ),
    "tip_t3_bg_exp": (
        "Legacy raw-1D background exposure in seconds; disabled with raw correction.",
        "旧版原始一维背景曝光时间（秒）；随原始校正禁用。",
    ),
    "tip_t3_bg_i0": (
        "Legacy raw-1D background beam monitor reading; disabled with raw correction.",
        "旧版原始一维背景入射光监测值；随原始校正禁用。",
    ),
    "tip_t3_bg_t": (
        "Legacy raw-1D background transmission fraction; disabled with raw correction.",
        "旧版原始一维背景透过率；随原始校正禁用。",
    ),
    "tip_t3_i0_semantic": (
        "Displays whether the beam monitor records counts per second or exposure totals. "
        "Scaled input is already adjusted for exposure; changing this will not redo it.",
        "显示入射光监测值是每秒计数还是曝光总计数；输入已换到相同曝光条件，修改此模式不会重做校正。",
    ),
    "tip_t3_buffer_enable": (
        "After conversion to intensity in cm⁻¹, subtract α times the buffer/solvent curve "
        "in the same units, with matching calibration and K.",
        "换成 cm⁻¹ 强度后，扣除 α 倍的同单位缓冲液或溶剂曲线；两者须使用相同标定记录和 K。",
    ),
    "tip_t3_buffer_file": (
        "Buffer/solvent curve with physical intensity units cm⁻¹, matching K and full calibration "
        "source information. Relative curves cannot be used here.",
        "已换成实际单位 cm⁻¹ 的缓冲液或溶剂曲线，须有相同 K 和完整标定来源；不能使用相对读数曲线。",
    ),
    "tip_t3_alpha": (
        "Positive multiplier for the buffer curve before subtraction; "
        "the result is sample intensity minus α × buffer intensity.",
        "缓冲液扣除前使用的正数倍数；结果为样品强度减去 α × 缓冲液强度。",
    ),
    "tip_t3_alpha_uncertainty": (
        "Standard uncertainty estimates the error size of buffer multiplier α. "
        "Leave blank if unknown; "
        "combined uncertainty then remains missing, not zero.",
        "缓冲液倍数 α 的标准不确定度，即估计误差大小；未知时留空，合成值保留为缺失，不设为零。",
    ),
    "tip_t3_buffer_status": (
        "Reports whether a buffer curve was loaded and validated, including its point count.",
        "显示缓冲液曲线是否已加载并通过校验，以及曲线点数。",
    ),
    "tip_t3_fluo_enable": (
        "Subtract fluorescence after absolute scaling and optional buffer subtraction; "
        "configure the chosen fluorescence method first.",
        "绝对强度换算和可选缓冲液扣除后再扣荧光；须先设置所选荧光方法。",
    ),
    "tip_mu_source": (
        "Choose the data used to estimate how strongly material weakens X-rays. "
        "NIST is limited to 30 keV; Elam accepts another energy and entered density.",
        "选择估计材料使 X 射线减弱程度所用的数据。NIST 仅限 30 keV；Elam 可填写其他能量与密度。",
    ),
    "tip_mu_energy": (
        "Photon energy in keV; leaving this field updates wavelength. "
        "Locked at 30 keV for the bundled NIST model.",
        "光子能量（keV）；离开输入栏后更新波长。内置 NIST 模型将此项锁定为 30 keV。",
    ),
    "tip_mu_wavelength": (
        "X-ray wavelength in Å; leaving this field updates energy. "
        "Locked for the NIST 30 keV model.",
        "X 射线波长（Å）；离开输入栏后更新能量。NIST 30 keV 模型锁定此项。",
    ),
    "tip_mu_preset": (
        "Fill typical material composition and, for Elam, density. "
        "Check these values against your specimen's measured properties.",
        "填写该材料的典型成分，并为 Elam 填写密度；请与自己样品的实测值核对。",
    ),
    "tip_mu_density": (
        "Mass per specimen volume in g/cm³, for Elam. NIST estimates density from "
        "composition assuming ideal volume addition and disables this field.",
        "单位样品体积的质量（g/cm³），供 Elam 使用。NIST 假定各成分体积可相加来估计密度，此栏禁用。",
    ),
    "tip_mu_porosity": (
        "Flag possible porosity for the NIST model's warning. It does not measure "
        "porosity or correct density; this option is disabled for Elam.",
        "为 NIST 模型标记可能存在孔隙，以记录警告；不会测量孔隙率或修正密度，Elam 不使用此项。",
    ),
    "tip_mu_composition": (
        "Enter each element's share of total mass, totalling 1 or 100, "
        "e.g. Ti:90, Al:6, V:4. Use mass shares, not atom-number shares.",
        "填写各元素占总质量的比例，总和为 1 或 100，如 Ti:90, Al:6, V:4；不是原子数量比例。",
    ),
    "tip_mu_result": (
        "Read the calculated attenuation, each element's contribution and sources. "
        "The estimate does not include all errors or establish measured thickness or density.",
        "查看计算的光衰减程度、各元素贡献和来源；估计未包含全部误差，不能据此确认实测厚度或密度。",
    ),
    "tip_mu_calculate": (
        "Estimate attenuation μ, the weakening of light per unit path length, and record "
        "inputs and detector settings. Fixed-thickness processing does not use this estimate.",
        "估计 μ（单位路径长度的光减弱程度），并记录输入与探测器设置；固定厚度处理不使用此估计值。",
    ),
    "tip_mu_export": (
        "Save composition, energy, sources and detector settings as JSON after calculation. "
        "Changed inputs or geometry require recalculation before export.",
        "计算后把成分、能量、来源和探测器设置保存为 JSON；输入或设置变化后须重新计算才能导出。",
    ),
    "tip_theme": ("Switch the interface between light and dark colours.", "切换界面的明亮与深色配色。"),
    "tip_language": (
        "Switch interface labels and help between English and Chinese.",
        "切换界面标签和帮助的中英文。",
    ),
    "tip_notebook": (
        "Select calibration, 2D processing or external 1D conversion. "
        "Shared calibration settings carry between pages.",
        "选择标定、二维处理或外部一维转换页；各页共用标定设置。",
    ),
    "tip_scrollbar": (
        "Drag to reveal controls outside the visible area; mouse-wheel scrolling "
        "also works in the form.",
        "拖动以显示可见区域之外的控件，也可在表单内用鼠标滚轮滚动。",
    ),
    "tip_plot_canvas": (
        "Inspect the current figure; use the toolbar to zoom, pan or save it. "
        "View changes do not recalculate data.",
        "查看当前图像；用工具栏缩放、平移或保存。改变视图不会重新计算数据。",
    ),
    "tip_plot_home": ("Restore the original plot view.", "恢复图像的初始视图。"),
    "tip_plot_back": ("Return to the previous plot view.", "返回上一个图像视图。"),
    "tip_plot_forward": ("Move to the next view in the plot history.", "前进到图像历史中的下一个视图。"),
    "tip_plot_pan": (
        "Enable pan mode, then drag the plot to move the visible range.",
        "启用平移后拖动图像，移动可见范围。",
    ),
    "tip_plot_zoom": (
        "Enable zoom mode, then drag a rectangle over the region to enlarge.",
        "启用缩放后拖出矩形，放大选定区域。",
    ),
    "tip_plot_subplots": (
        "Adjust subplot spacing and margins so axes and labels fit in the figure.",
        "调整子图间距和边距，使坐标轴与标签完整显示。",
    ),
    "tip_plot_save": (
        "Save the displayed figure using the plot toolbar's file dialog.",
        "通过图形工具栏的文件窗口保存当前图像。",
    ),
    "tip_plot_customize": (
        "Edit plot axes and curve appearance; changes affect the figure, not measured values.",
        "修改坐标轴和曲线外观；只改变图像，不改变测量数值。",
    ),
    "tip_help_text": (
        "Read the operating steps and parameter explanations; scroll to continue.",
        "这里是操作步骤和参数说明，向下滚动可继续阅读。",
    ),
    "tip_help_topic": ("Select a help topic to display its explanation.", "选择帮助主题并显示说明。"),
    "tip_fluo_enable": (
        "Enable fluorescence subtraction after absolute scaling; provide the selected "
        "method's intensity, window or measured curve first.",
        "启用绝对强度换算后的荧光扣除；须先提供所选方法需要的强度、区间或实测曲线。",
    ),
    "tip_fluo_status": (
        "Shows whether fluorescence correction is configured; Dry Check validates "
        "the actual values and source curve before processing.",
        "显示荧光校正是否已设置；处理前由预检查核对实际参数与来源曲线。",
    ),
    "tip_result_text": (
        "Read calculation results, warnings and source records; select text to copy it.",
        "阅读计算结果、警告和来源记录，可选择文字复制。",
    ),
    "tip_scrollarea": (
        "Scroll to reach controls below the visible area; the scrollbar shows your position.",
        "滚动以查看可见区域下方的控件；滚动条显示当前位置。",
    ),
    "tip_tab_calibration": (
        "Start here: compare a measured standard with known scattering to calculate K.",
        "从此页开始：把实测标准样与已知散射强度比较，计算 K。",
    ),
    "tip_tab_batch": (
        "Process detector images using the calibration record, fixed thickness and "
        "selected integration regions.",
        "用标定记录、固定厚度和所选积分区域处理探测器图像。",
    ),
    "tip_tab_external": (
        "Convert reduced relative 1D profiles to absolute intensity using verified K; "
        "raw-1D correction is disabled.",
        "用已验证的 K 把已校正相对强度一维曲线换成绝对强度；原始一维校正已禁用。",
    ),
    "tip_tab_help": ("Read workflow instructions and parameter explanations.", "查看操作步骤和参数说明。"),
    "tip_calibration_load": (
        "Load a complete saved calibration record. Apply it only after its sources "
        "and measurement settings pass validation.",
        "加载保存的完整标定记录；通过来源和测量设置校验后才应用。",
    ),
    "tip_activity_report": (
        "Open the current operation log and check reports to read warnings and failures.",
        "打开当前操作日志和检查报告，查看警告与失败原因。",
    ),
    "tip_details": (
        "Expand or collapse the legacy raw-1D fields. Showing them does not "
        "enable raw correction or its disabled controls.",
        "展开或收起旧版原始一维参数；显示参数不会启用原始校正或被禁用的控件。",
    ),
    "tip_results_notebook": (
        "Switch between the calibration plot and the written result report.",
        "切换查看标定图像与文字报告。",
    ),
    "tip_panedwindow": (
        "Drag the divider to give more width to the parameter form or the results.",
        "拖动分隔线，调整参数表单与结果区域的宽度。",
    ),
    "tip_theme_unavailable": (
        "Colour switching is unavailable because the optional theme component is not installed.",
        "未安装可选主题组件，当前无法切换明亮与深色配色。",
    ),
}

_OPTION_PAIRS = {
    "mu_source_nist": (
        "Use bundled attenuation data at 30 keV and calculate density from element proportions.",
        "使用内置的 30 keV 光减弱数据，并按元素比例估算密度。",
    ),
    "mu_source_elam": (
        "Use the xraydb data library with your X-ray energy and material density.",
        "使用 xraydb 数据库，并填写实际 X 射线能量和材料密度。",
    ),
    "material": (
        "Fill the element proportions by mass: {composition}.",
        "填入各元素占总质量的比例：{composition}。",
    ),
    "material_density": (
        " Also fill the preset density: {density} g/cm³.",
        "同时填入预设密度：{density} g/cm³。",
    ),
    "rate": (
        "I0 is counts per second; normalize by exposure × I0 × transmission.",
        "I0 是每秒计数；除以曝光时间 × I0 × 透过率。",
    ),
    "integrated": (
        "I0 is total counts during exposure; normalize by I0 × transmission.",
        "I0 是整次曝光总计数；除以 I0 × 透过率。",
    ),
    "azimuthal": (
        "Estimate the error size of integrated intensity from differences around a detector ring.",
        "根据探测器环内各方向的强度差异，估计积分强度的误差大小。",
    ),
    "poisson": (
        "Estimate intensity error size from random fluctuations in the number of counted photons.",
        "根据光子计数的随机波动，估计强度的误差大小。",
    ),
    "none": (
        "Do not estimate integration error size; a missing estimate does not mean zero error.",
        "不估计积分误差大小；没有估计值不表示误差为零。",
    ),
    "constant": (
        "Subtract β times the entered constant fluorescence F0, in cm⁻¹.",
        "扣除 β 倍的已填常数荧光强度 F0，单位为 cm⁻¹。",
    ),
    "high_q_mean": (
        "Use the mean intensity in the high-q window to estimate fluorescence; "
        "sample scattering in that window must be negligible.",
        "用高 q 区间的平均强度估计荧光；此区间的样品散射须可忽略。",
    ),
    "high_q_median": (
        "Use the median intensity in the high-q window to estimate fluorescence; "
        "sample scattering in that window must be negligible.",
        "用高 q 区间的强度中位数估计荧光；此区间的样品散射须可忽略。",
    ),
    "measured": (
        "Subtract β times a measured absolute fluorescence curve F(q), in cm⁻¹.",
        "扣除 β 倍的实测绝对荧光曲线 F(q)，单位为 cm⁻¹。",
    ),
    "auto": (
        "Read explicitly labelled axis units from the input; unknown or ambiguous "
        "axes are blocked rather than guessed.",
        "从输入读取明确标记的坐标单位；未知或含糊的坐标会阻止输出，不作猜测。",
    ),
    "q_A^-1": (
        "Input q is in Å⁻¹: the plot coordinate corresponding to scattering angle "
        "at the measurement wavelength.",
        "输入 q 单位为 Å⁻¹，是该测量波长下与散射角对应的曲线位置坐标。",
    ),
    "two_theta_deg": (
        "Input is scattering angle 2θ in degrees; provide wavelength in Å to convert to q.",
        "输入是散射角 2θ（度）；须提供波长（Å）才能换成 q。",
    ),
    "chi_deg": (
        "Input is angle χ around the beam in degrees, not the scattering-angle coordinate q.",
        "输入是束心周围的方向角 χ（度），与散射坐标 q 不同。",
    ),
    "float32": (
        "Save 2D pixels as 32-bit floating-point values to use less disk space.",
        "以 32 位浮点数保存二维像素，减少磁盘占用。",
    ),
    "float64": (
        "Save 2D pixels as 64-bit floating-point values to retain more numerical digits; "
        "this does not increase measurement accuracy.",
        "以 64 位浮点数保存二维像素，保留更多数值位数；不会提高测量准确度。",
    ),
    "std_srm3600": (
        "Use the built-in NIST SRM 3600 glassy-carbon certificate curve and fixed "
        "certificate thickness.",
        "使用内置 NIST SRM 3600 玻璃碳证书曲线及固定的证书厚度。",
    ),
    "std_water": (
        "Use a temperature-dependent water reference; enter measured temperature "
        "from 4 to 40 °C and the water path length.",
        "使用随温度变化的水参考强度；填写 4–40 °C 范围内的实测温度及水层厚度。",
    ),
    "std_lupolen": (
        "Load the absolute reference curve for this Lupolen batch and enter its thickness.",
        "加载此批次 Lupolen 的绝对参考曲线，并填写厚度。",
    ),
    "std_custom": (
        "Provide your standard's absolute reference curve with explicit q units "
        "and enter its measured thickness.",
        "提供标准样的绝对参考曲线并明确 q 单位，同时填写实测厚度。",
    ),
    "fmt_tsv": (
        "Save a text table with tab-separated columns, readable by spreadsheets and scripts.",
        "保存以制表符分隔列的文本表格，便于表格软件和脚本读取。",
    ),
    "fmt_csv": (
        "Save a text table with comma-separated columns.",
        "保存以逗号分隔列的文本表格。",
    ),
    "fmt_dat": (
        "Save a plain-text profile for scientific analysis software.",
        "保存供科学分析软件读取的纯文本曲线。",
    ),
    "fmt_xml": (
        "Save canSAS XML with a q axis in Å⁻¹ and metadata; unavailable for angle-axis profiles.",
        "保存带 q 轴（Å⁻¹）和元数据的 canSAS XML，不能用于角度坐标曲线。",
    ),
    "fmt_h5": (
        "Save NXcanSAS HDF5 with q data and metadata; requires HDF5 support and a q axis.",
        "保存带 q 数据和元数据的 NXcanSAS HDF5；须有 HDF5 支持及 q 轴。",
    ),
    "plot_png": (
        "Save a raster image suitable for documents and screen viewing.",
        "保存适合文档和屏幕查看的像素图。",
    ),
    "plot_tiff": (
        "Save a high-resolution raster image; its detail depends on the selected resolution.",
        "保存高分辨率像素图；图像细节取决于所选分辨率。",
    ),
    "plot_pdf": (
        "Save a PDF figure with vector lines and text for printing or sharing.",
        "保存带矢量线条和文字的 PDF 图像，便于打印或分享。",
    ),
    "plot_svg": (
        "Save an SVG figure with editable vector lines and text.",
        "保存可编辑矢量线条和文字的 SVG 图像。",
    ),
    "plot_eps": (
        "Save an EPS vector figure for compatible publication workflows.",
        "保存供兼容的出版流程使用的 EPS 矢量图像。",
    ),
    "Raw inspection": (
        "Use the larger, lower-resolution preset for inspecting detector data on screen.",
        "使用较大尺寸、较低分辨率的预设，在屏幕上检查探测器数据。",
    ),
    "Publication": (
        "Use the 600 dpi preset with compact text and line widths for publication figures.",
        "使用 600 dpi 预设及紧凑字号和线宽，制作论文图像。",
    ),
    "Presentation": (
        "Use larger text and thicker lines for slides and projected figures.",
        "使用较大字号和较粗线条，制作幻灯片和投影图像。",
    ),
    "Single-column figure": (
        "Use a 3.45-inch-wide, 600 dpi figure sized for a single journal column.",
        "使用宽 3.45 英寸、600 dpi 的图像，适配期刊单栏。",
    ),
    "Double-column figure": (
        "Use a 7.10-inch-wide, 600 dpi figure sized for two journal columns.",
        "使用宽 7.10 英寸、600 dpi 的图像，适配期刊双栏。",
    ),
}


def _language_dicts(pairs: dict[str, tuple[str, str]]) -> dict[str, dict[str, str]]:
    return {
        "en": {key: pair[0] for key, pair in pairs.items()},
        "zh": {key: pair[1] for key, pair in pairs.items()},
    }


EXTRA_HELP = _language_dicts(_EXTRA_PAIRS)
HELP_TEXT = _language_dicts(_HELP_PAIRS | _EXTRA_PAIRS)
OPTION_HELP = _language_dicts(_OPTION_PAIRS)
