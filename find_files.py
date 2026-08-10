import os
import csv
import shutil
import logging


def setup_logger():
    """配置日志记录器"""
    logger = logging.getLogger('FileSync')
    logger.setLevel(logging.INFO)

    # 创建控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # 创建文件处理器
    fh = logging.FileHandler('file_sync.log', mode='w')
    fh.setLevel(logging.DEBUG)

    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


def find_and_copy_missing_files(csv_path, source_dir, output_dir):
    logger = setup_logger()
    logger.info("===== 开始处理缺失文件 =====")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录已创建: {output_dir}")

    # 步骤1: 从CSV读取已记录的文件名
    recorded_filenames = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 跳过标题行
            logger.info(f"CSV标题行: {header}")

            for row_num, row in enumerate(reader, 2):
                if not row:  # 跳过空行
                    continue

                # 提取路径并获取文件名
                filepath = row[0].strip()
                if not filepath:
                    continue

                # 提取纯文件名 (不含路径)
                filename = os.path.basename(filepath)
                recorded_filenames.add(filename)
                logger.debug(f"CSV行 {row_num}: 记录文件名 '{filename}'")

        logger.info(f"CSV中总共找到 {len(recorded_filenames)} 个唯一文件名")
    except Exception as e:
        logger.error(f"读取CSV时出错: {str(e)}")
        return

    # 步骤2: 扫描源代码目录中的所有.py文件
    source_files = {}
    for root, _, files in os.walk(source_dir):
        for file in files:
            # if file.endswith('.py'):
            if file.endswith('.java'):
                abs_path = os.path.join(root, file)
                source_files[file] = abs_path  # 存储文件名->完整路径映射
                logger.debug(f"发现源文件: {file} -> {abs_path}")

    logger.info(f"源代码目录中找到 {len(source_files)} 个.py文件")

    # 步骤3: 找出CSV中缺失的文件
    missing_files = []
    for filename, abs_path in source_files.items():
        if filename not in recorded_filenames:
            missing_files.append((filename, abs_path))
            logger.info(f"发现缺失文件: {filename}")

    if not missing_files:
        logger.info("没有发现缺失文件!")
        return

    # 步骤4: 复制缺失文件到新文件夹
    logger.info(f"发现 {len(missing_files)} 个缺失文件，开始复制...")
    copied_count = 0

    for filename, src_path in missing_files:
        try:
            dest_path = os.path.join(output_dir, filename)

            # 避免覆盖同名文件
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while True:
                    new_filename = f"{base}_{counter}{ext}"
                    new_dest = os.path.join(output_dir, new_filename)
                    if not os.path.exists(new_dest):
                        dest_path = new_dest
                        logger.warning(f"文件重名! 重命名为: {new_filename}")
                        break
                    counter += 1

            shutil.copy2(src_path, dest_path)
            copied_count += 1
            logger.info(f"已复制: {filename} -> {dest_path}")
        except Exception as e:
            logger.error(f"复制 {filename} 失败: {str(e)}")

    logger.info(f"操作完成! 成功复制 {copied_count}/{len(missing_files)} 个文件到 {output_dir}")


def _sync_csv_recorded_files(csv_path, source_dir, output_dir, action):
    """
    从 CSV 中读取文件路径，按原有目录结构同步（复制或移动）到输出目录。

    公共实现，供 copy_csv_recorded_files 与 move_csv_recorded_files 复用，
    避免路径计算与冲突处理逻辑重复。

    CSV 格式：第一列为文件路径（绝对或相对路径），后续列可选。
    同步时：
      - 若文件在 source_dir 下，则保留其相对路径结构。
      - 否则，将盘符作为顶级目录（如 'C'），后接剩余路径，确保唯一性。
      - 若目标文件已存在且内容相同则跳过；内容不同则自动重命名（添加数字后缀）。
      - 移动模式下，源文件位于输出目录内时跳过，避免自移动。

    参数:
        csv_path: CSV 文件路径
        source_dir: 源文件根目录（用于计算相对路径）
        output_dir: 输出目录
        action: 'copy' 使用 shutil.copy2；'move' 使用 shutil.move

    返回:
        (success_count, skipped_count, not_found_count, conflict_count)
    """
    if action not in ('copy', 'move'):
        raise ValueError(f"不支持的 action: {action}（仅支持 'copy' 或 'move'）")

    logger = setup_logger()
    verb = '复制' if action == 'copy' else '移动'
    logger.info(f"===== 开始{verb}CSV记录的文件（保留目录结构 + 冲突处理）=====")

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录已创建: {output_dir}")

    # 标准化为绝对路径，用于相对路径计算与自移动防护
    source_dir_abs = os.path.abspath(source_dir)
    output_dir_abs = os.path.abspath(output_dir)

    # 读取CSV，获取所有文件路径
    file_paths = []
    try:
        # 尝试 UTF-8，失败则用 GBK
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                logger.info(f"CSV标题行: {header}")
                for row in reader:
                    if row and row[0].strip():
                        file_paths.append(row[0].strip())
        except UnicodeDecodeError:
            with open(csv_path, 'r', encoding='gbk') as f:
                reader = csv.reader(f)
                header = next(reader)
                logger.info(f"CSV标题行: {header} (使用GBK编码)")
                for row in reader:
                    if row and row[0].strip():
                        file_paths.append(row[0].strip())
        logger.info(f"CSV中总共找到 {len(file_paths)} 个文件路径")
    except Exception as e:
        logger.error(f"读取CSV时出错: {str(e)}")
        return 0, 0, 0, 0

    success_count = 0
    skipped_count = 0
    not_found_count = 0
    conflict_count = 0

    for raw_path in file_paths:
        # 确定源文件的绝对路径
        if os.path.isabs(raw_path):
            src_path = raw_path
        else:
            src_path = os.path.join(source_dir, raw_path)

        src_path = os.path.normpath(src_path)

        if not os.path.exists(src_path):
            logger.warning(f"文件不存在: {src_path}")
            not_found_count += 1
            continue

        src_abs = os.path.abspath(src_path)

        # 移动模式：源文件位于输出目录内（含相等）时跳过，避免自移动
        if action == 'move' and (src_abs == output_dir_abs or
                                 src_abs.startswith(output_dir_abs + os.sep)):
            logger.warning(f"源文件位于输出目录内，跳过{verb}: {src_path}")
            skipped_count += 1
            continue

        # 构建唯一的目标相对路径
        rel_path = None

        # 优先基于 source_dir 计算相对路径
        try:
            if src_abs.startswith(source_dir_abs):
                rel_path = os.path.relpath(src_abs, source_dir_abs)
        except ValueError:
            pass  # 跨盘符等异常

        if rel_path is None:
            # 无法基于 source_dir，则基于盘符构建路径（例如 'C:/a/b.py' -> 'C/a/b.py'）
            drive, tail = os.path.splitdrive(src_abs)
            if drive:
                # 去掉冒号，将盘符作为一级目录
                drive_clean = drive.rstrip(':')
                rel_path = os.path.join(drive_clean, tail.lstrip(os.sep))
            else:
                # 无盘符（Linux），直接使用绝对路径去掉前导斜杠
                rel_path = src_abs.lstrip(os.sep)

        dest_path = os.path.normpath(os.path.join(output_dir, rel_path))

        # 处理目标文件已存在的情况
        if os.path.exists(dest_path):
            # 简单比较文件大小和修改时间，判断是否相同（可根据需求调整）
            if (os.path.getsize(src_path) == os.path.getsize(dest_path) and
                    os.path.getmtime(src_path) == os.path.getmtime(dest_path)):
                logger.warning(f"目标文件已存在且相同，跳过: {dest_path}")
                skipped_count += 1
                continue
            else:
                # 不同文件，生成唯一名称
                base, ext = os.path.splitext(dest_path)
                counter = 1
                while True:
                    new_dest = f"{base}_{counter}{ext}"
                    if not os.path.exists(new_dest):
                        dest_path = new_dest
                        logger.warning(f"文件冲突，重命名为: {os.path.basename(new_dest)}")
                        conflict_count += 1
                        break
                    counter += 1

        # 确保目标目录存在
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        try:
            if action == 'copy':
                shutil.copy2(src_path, dest_path)
            else:
                shutil.move(src_path, dest_path)
            success_count += 1
            logger.info(f"已{verb}: {src_path} -> {dest_path}")
        except Exception as e:
            logger.error(f"{verb} {src_path} 失败: {str(e)}")

    # 输出统计报告
    logger.info(f"操作完成! 成功{verb} {success_count} 个文件")
    if skipped_count > 0:
        logger.warning(f"跳过 {skipped_count} 个文件")
    if conflict_count > 0:
        logger.warning(f"因冲突重命名 {conflict_count} 个文件")
    if not_found_count > 0:
        logger.warning(f"未找到 {not_found_count} 个文件")

    return success_count, skipped_count, not_found_count, conflict_count


def copy_csv_recorded_files(csv_path, source_dir, output_dir):
    """
    从 CSV 中读取文件路径，按原有目录结构复制到输出目录，确保不遗漏任何文件。

    参数:
        csv_path: CSV 文件路径
        source_dir: 源文件根目录（用于计算相对路径）
        output_dir: 输出目录

    返回:
        (copied_count, skipped_count, not_found_count, conflict_count)
    """
    return _sync_csv_recorded_files(csv_path, source_dir, output_dir, action='copy')


def move_csv_recorded_files(csv_path, source_dir, output_dir):
    """
    从 CSV 中读取文件路径，按原有目录结构移动到输出目录，确保不遗漏任何文件。

    与 copy_csv_recorded_files 行为一致，区别在于使用 shutil.move 移动文件
    （源位置文件会被移走，属不可逆操作，使用前请确认或备份）。
    移动模式下，源文件位于输出目录内时将跳过，以避免自移动。

    参数:
        csv_path: CSV 文件路径
        source_dir: 源文件根目录（用于计算相对路径）
        output_dir: 输出目录

    返回:
        (moved_count, skipped_count, not_found_count, conflict_count)
    """
    return _sync_csv_recorded_files(csv_path, source_dir, output_dir, action='move')


if __name__ == "__main__":
    # 配置参数 (根据实际情况修改)
    # CSV_FILE = "./pysafe_trapfile/py_code_analysis_qwenlong_trapfile_new-rule.csv"  # CSV文件路径
    # CSV_FILE = "./pysafe_trapfile/adv_trapfile.csv"  # CSV文件路径
    # SOURCE_DIR = "./pysafe_trapfile/"  # 源代码文件夹
    # OUTPUT_DIR = "./pysafe_trapfile/advance_trapfile"  # 文件输出文件夹
    # CSV_FILE = "./Java_newtest/Two_Interproc(2methods).csv"  # CSV文件路径
    # SOURCE_DIR = "./Java_newtest/"  # 源代码文件夹
    # OUTPUT_DIR = "./Java_newtest/Two_Interproc"  # 文件输出文件夹
    # CSV_FILE = "./cryptoapi/classify_by_type/Weak Password in keyStore.csv"  # CSV文件路径
    # SOURCE_DIR = "./cryptoapi/full171"  # 源代码文件夹
    # OUTPUT_DIR = "./cryptoapi/classify_by_type/Weak Password in keyStore"  # 文件输出文件夹
    # CSV_FILE = "./cryptolation_report_Python_Projects_filename.csv"  # CSV文件路径
    # CSV_FILE = "./bandit_report_Python_Projects_filename.csv"  # CSV文件路径
    # CSV_FILE = "./dlint_report_Python_Projects_filename.csv"  # CSV文件路径
    CSV_FILE = "./filename.csv"  # CSV文件路径
    SOURCE_DIR = r"D:\FALD\Python_Projects"  # 源代码文件夹
    OUTPUT_DIR = "./Filtered_out"  # 文件输出文件夹

    print(f"开始处理: CSV={CSV_FILE}, 源目录={SOURCE_DIR}, 输出目录={OUTPUT_DIR}")
    # find_and_copy_missing_files(CSV_FILE, SOURCE_DIR, OUTPUT_DIR)
    # copy_csv_recorded_files(CSV_FILE, SOURCE_DIR, OUTPUT_DIR)
    move_csv_recorded_files(CSV_FILE, SOURCE_DIR, OUTPUT_DIR)
    # print("处理完成! 详情请查看日志文件: file_sync.log")
