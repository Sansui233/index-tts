import torch
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 是否可用: {torch.cuda.is_available()}")
print(f"CUDA 版本: {torch.version.cuda}")


try:
    from indextts.BigVGAN.alias_free_activation.cuda import anti_alias_activation_cuda
    print("Loaded anti_alias_activation_cuda from indextts.BigVGAN.alias_free_activation.cuda", anti_alias_activation_cuda)
except ImportError:
    import importlib
    import os
    try:
        anti_alias_activation_cuda = importlib.import_module("anti_alias_activation_cuda", "indextts.BigVGAN.alias_free_activation.cuda")
        print("Loaded anti_alias_activation_cuda from importlib.import_module", anti_alias_activation_cuda)
    except ImportError as e:
        for path in [
            'indextts/BigVGAN/alias_free_activation/cuda',
            os.path.abspath("indextts/BigVGAN/alias_free_activation/cuda"),
        ]:
            for f in os.listdir(path):
                if f.startswith("anti_alias_activation_cuda") and f.endswith(".pyd"):
                    pyd_file = os.path.join(path, f)
                    break
            print(f"Found anti_alias_activation_cuda at {pyd_file}")
            spec = importlib.util.spec_from_file_location("anti_alias_activation_cuda", pyd_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"Loaded anti_alias_activation_cuda from {pyd_file}")        
            break
