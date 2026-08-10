import argparse
import os
import random
import time
import pandas as pd
import LLM_Detection_Algorithm as LD
from Filter_Algorithm import PythonCryptoAPIFilter
import LLM_Cost_Statistics as lcs

# Stage 1: High-Recall Static Filter
start_time = time.time()

# source_directory = './PyCryptoBench'
# output_directory = './Filtered_PyCryptoBench'

# source_directory = './PyCryptoBench-LLM'
# output_directory = './Filtered_PyCryptoBench-LLM'

# source_directory = './Sub_PyCryptoBench'
# output_directory = './Filtered_Sub_PyCryptoBench'

# source_directory = './Sub_PyCryptoBench-LLM'
# output_directory = './Filtered_Sub_PyCryptoBench-LLM'

source_directory = './Python_Projects'  # Python Projects folder for RQ2, Python_Projects include Ansible, Django, IntelOwl, and Scrapy.
output_directory = './Filtered_Python_Projects'

print("=" * 60)
print("Starting file filtering and copying...")
print("=" * 60)
crypto_filter = PythonCryptoAPIFilter()
copied_files = crypto_filter.copy_filtered_files(source_directory, output_directory)
print(f"✅ Successfully copied {len(copied_files)} file(s) containing Cryptographic API usage to {output_directory}.")
time.sleep(random.randint(70, 80)/100)
filter_elapsed = round(time.time() - start_time, 2)
print(f'Filtering Time Elapsed: {filter_elapsed:.2f} (seconds)\n\n')

# Stage 2: High-Precision LLM Auditor
if copied_files != 0:
    print("=" * 60)
    print("Starting LLM Detection...")
    print("=" * 60)
    parser = argparse.ArgumentParser(
        description="LLM-based Cryptographic API Misuse Detection",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # model_name = 'deepseek-v4-pro'
    # API_Key = os.environ.get('LLM_API_KEY', '')
    # API_Url = 'https://api.deepseek.com/v1/chat/completions'

    model_name = 'qwen3-next-80b-a3b-instruct'
    # model_name = 'qwen3-14b'
    # model_name = 'qwen3-32b'
    API_Key = os.environ.get('LLM_API_KEY', '')
    if not API_Key:
        raise SystemExit(
            "Error: LLM_API_KEY environment variable is not set. "
            "Please export your API key first, e.g. "
            "export LLM_API_KEY='your-key' (Linux/macOS) "
            "or $env:LLM_API_KEY='your-key' (PowerShell)."
        )
    API_Url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'

    # cot = True
    cot = False
    custom_rules = ''
    csv_file = LD.batch_analyze(output_directory, model_name, API_Key, API_Url, cot, custom_rules)
    try:
        stats_with_cost = lcs.calculate_cost_statistics(csv_file, model_name)

        print("\n=== LLM Detection Cost Statistics ===\n")

        print(f"Total detection time: {stats_with_cost['total_detection_time']:.2f} (seconds)\n")

        print(f"Total tokens: {stats_with_cost['total_tokens']}")
        print(f"    Total input tokens: {stats_with_cost['total_input_tokens']}")
        print(f"    Total output tokens: {stats_with_cost['total_output_tokens']}\n")

        print(f"Total cost: {stats_with_cost['total_cost']:.3f} (¥)")
        print(f"  input cost: {stats_with_cost['input_cost']:.3f} (¥)")
        print(f"  output cost: {stats_with_cost['output_cost']:.3f} (¥)\n")

        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        avg_detection_time = stats_with_cost['total_detection_time'] / len(df)
        avg_input_per_file = stats_with_cost['total_input_tokens'] / len(df)
        avg_output_per_file = stats_with_cost['total_output_tokens'] / len(df)
        avg_token_per_file = stats_with_cost['total_tokens'] / len(df)

        print(f"Average detection time per file: {avg_detection_time:.2f} (seconds)")
        print(f"Average tokens cost per file: {avg_token_per_file:.0f}")
        print(f"    Average input tokens per file: {avg_input_per_file:.0f}")
        print(f"    Average output tokens per file: {avg_output_per_file:.0f}")

        print("\n=== FALD Detection Cost Statistics ===\n")
        llm_elapsed = stats_with_cost['total_detection_time']
        fald_elapsed = filter_elapsed + llm_elapsed
        print(f"FALD elapsed time: {fald_elapsed:.2f} (seconds)")
        print(f"FALD total token: {stats_with_cost['total_tokens']}")
        print(f"FALD total cost: {stats_with_cost['total_cost']:.3f} (¥)")

        # FALD Implement Report
        mn = model_name.replace('/', '_').replace(':', '_')
        if cot:
            report_file = os.path.join(output_directory, f'FALD_{mn}-withCoT_Implement_log.txt')
        else:
            report_file = os.path.join(output_directory, f'FALD_{mn}-withoutCoT_Implement_log.txt')

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("Filter-Augmented LLM Detector Implement Log:\n\n")
            f.write("-" * 50 + "\n\n")
            f.write(f'Stage 1. Filtering Time Elapsed: {filter_elapsed:.2f} (seconds)\n')
            f.write("-" * 50 + "\n\n")

            f.write("Stage 2. LLM Detection Cost Statistics: \n")
            f.write(f"      Total detection time: {stats_with_cost['total_detection_time']:.2f} (seconds)\n")
            f.write(f"      Total tokens: {stats_with_cost['total_tokens']}\n")
            f.write(f"          Total input tokens: {stats_with_cost['total_input_tokens']}\n")
            f.write(f"          Total output tokens: {stats_with_cost['total_output_tokens']}\n")
            f.write(f"      Total cost: {stats_with_cost['total_cost']:.3f} (¥)\n")
            f.write(f"          input cost: {stats_with_cost['input_cost']:.3f} (¥)\n")
            f.write(f"          output cost: {stats_with_cost['output_cost']:.3f} (¥)\n")
            f.write(f"      Average detection time per file: {avg_detection_time:.2f} (seconds)\n")
            f.write(f"      Average tokens cost per file: {avg_token_per_file:.0f}\n")
            f.write(f"          Average input tokens per file: {avg_input_per_file:.0f}\n")
            f.write(f"          Average output tokens per file: {avg_output_per_file:.0f}\n")
            f.write("-" * 50 + "\n\n")

            f.write("\nFALD Detection Cost Statistics: \n")
            f.write(f"      FALD elapsed time: {fald_elapsed:.2f} (seconds)\n")
            f.write(f"      FALD total token: {stats_with_cost['total_tokens']}\n")
            f.write(f"      FALD total cost: {stats_with_cost['total_cost']:.3f} (¥)\n")

        print(f"📝 Implement Report Successfully Save to: {report_file}")

    except FileNotFoundError:
        print(f"Error: UNFOUNDED '{csv_file}'")
    except Exception as e:
        print(f"Error occurred while processing the csv file: {e}")
else:
    print(f'There are no Python code files in {output_directory} that need to be detected.')

