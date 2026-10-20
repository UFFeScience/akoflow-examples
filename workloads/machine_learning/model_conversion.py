def model_conversion():
    if STAGE == 'load-model':return {'weight':INPUT['weight'],'bias':INPUT['bias'],'inputs':INPUT['inputs']}
    if STAGE == 'export-onnx':
        import numpy as np
        import onnx
        from onnx import helper, TensorProto, numpy_helper
        data=previous()
        graph=helper.make_graph([helper.make_node('Mul',['x','w'],['product']),helper.make_node('Add',['product','b'],['y'])], 'linear', [helper.make_tensor_value_info('x',TensorProto.FLOAT,[None,1])], [helper.make_tensor_value_info('y',TensorProto.FLOAT,[None,1])], [numpy_helper.from_array(np.array([data['weight']],dtype=np.float32),'w'),numpy_helper.from_array(np.array([data['bias']],dtype=np.float32),'b')])
        model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',18)])
        onnx.checker.check_model(model);onnx.save(model,str(OUT/'model.onnx'))
        return {'format':'ONNX','bytes':(OUT/'model.onnx').stat().st_size}
    if STAGE == 'export-torchscript':
        import torch
        data=previous();layer=torch.nn.Linear(1,1)
        with torch.no_grad():layer.weight.fill_(data['weight']);layer.bias.fill_(data['bias'])
        traced=torch.jit.trace(layer,torch.tensor([[0.]],dtype=torch.float32))
        traced.save(str(OUT/'model.torchscript.pt'))
        return {'format':'TorchScript','bytes':(OUT/'model.torchscript.pt').stat().st_size}
    if STAGE == 'quantize-cpu':
        import onnx
        from onnx import numpy_helper
        exported=onnx.load(str(OUT/'model.onnx'))
        tensors={tensor.name:numpy_helper.to_array(tensor) for tensor in exported.graph.initializer}
        weight=float(tensors['w'][0]);bias=float(tensors['b'][0]);scale=max(abs(weight)/127,1e-12);integer=round(weight/scale)
        quantized={'dtype':'int8','weight':integer,'scale':scale,'bias':bias}
        write_json('model-int8.json',quantized);return quantized
    if STAGE == 'quantize-gpu':
        import torch
        exported=torch.jit.load(str(OUT/'model.torchscript.pt'))
        parameters=exported.state_dict()
        values=[float(parameters['weight'][0][0]),float(parameters['bias'][0])];raw=struct.pack('<ee',*values)
        (OUT/'model-fp16.bin').write_bytes(raw)
        return {'dtype':'float16','values':list(struct.unpack('<ee',raw)),'hardware':'CPU conversion; GPU-compatible coefficient storage, no TensorRT engine'}
    if STAGE == 'validate-outputs':
        import numpy as np
        import onnx
        import torch
        from onnx.reference import ReferenceEvaluator
        inputs=np.array(INPUT['inputs'],dtype=np.float32).reshape(-1,1)
        expected=inputs*INPUT['weight']+INPUT['bias']
        onnx_output=ReferenceEvaluator(onnx.load(str(OUT/'model.onnx'))).run(None,{'x':inputs})[0]
        script=torch.jit.load(str(OUT/'model.torchscript.pt'));script_output=script(torch.from_numpy(inputs)).detach().numpy()
        q=read_stage('quantize-cpu');half=read_stage('quantize-gpu')['values']
        errors={'onnx':float(np.max(np.abs(onnx_output-expected))),'torchscript':float(np.max(np.abs(script_output-expected))),'int8':max(abs((q['weight']*q['scale'])*x+q['bias']-(INPUT['weight']*x+INPUT['bias'])) for x in INPUT['inputs']),'float16':max(abs(half[0]*x+half[1]-(INPUT['weight']*x+INPUT['bias'])) for x in INPUT['inputs'])}
        require(max(errors.values())<0.01,'converted variants differ beyond tolerance')
        write_json('validation.json',{'maxAbsoluteErrors':errors,'inputs':len(INPUT['inputs'])});return errors
    if STAGE == 'publish-variants':return {'validatedVariants':previous(),'formats':['ONNX','TorchScript','int8 JSON coefficients','IEEE float16 coefficients']}
    raise ValueError(STAGE)


def compute():
    return model_conversion()
