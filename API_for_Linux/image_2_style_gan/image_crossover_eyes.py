# import argparse
import random
import os
import shutil
import sys
import numpy as np
from collections import OrderedDict
from skimage.io import imread, imsave
from skimage.exposure import match_histograms

import torch
import torch.nn as nn
import torch.optim as optim
from image_2_style_gan.align_images import align_images
from image_2_style_gan.mask_makers.precision_mask_maker import precision_eye_masks
from image_2_style_gan.read_image import *
from image_2_style_gan.perceptual_model import VGG16_for_Perceptual
from image_2_style_gan.stylegan_layers import G_mapping, G_synthesis
from torchvision.utils import save_image

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'


def image_crossover_eyes(BASE_DIR, RAW_DIR, rand_uuid, process_selection, gender):
    ALIGNED_IMAGE_DIR = f'{BASE_DIR}aligned/'
    os.mkdir(ALIGNED_IMAGE_DIR)

    TARGET_IMAGE_DIR = f'{BASE_DIR}target/'
    os.mkdir(TARGET_IMAGE_DIR)

    if process_selection == 0 and gender == 'female':
        TARGET_SOURCE_DIR = '../image_2_style_gan/source/target/female/'
    elif process_selection == 0 and gender == 'male':
        TARGET_SOURCE_DIR = '../image_2_style_gan/source/target/male/'
    else:
        TARGET_SOURCE_DIR = f'{BASE_DIR}raw_target/aligned/'

    FINAL_IMAGE_DIR = f'{BASE_DIR}final/'
    os.mkdir(FINAL_IMAGE_DIR)

    MASK_DIR = f'{BASE_DIR}mask/'
    os.mkdir(MASK_DIR)

    model_resolution = 1024

    # parser = argparse.ArgumentParser(
    #     description='Find latent representation of reference images using perceptual loss')
    # parser.add_argument('--batch_size', default=1,
    #                     help='Batch size for generator and perceptual model', type=int)
    # parser.add_argument('--resolution', default=model_resolution, type=int)
    # parser.add_argument('--src_im1', default=TARGET_IMAGE_DIR)
    # parser.add_argument('--src_im2', default=ALIGNED_IMAGE_DIR)
    # # parser.add_argument('--mask', default=MASK_DIR)
    # parser.add_argument(
    #     '--weight_file', default=f"../image_2_style_gan/torch_weight_files/karras2019stylegan-ffhq-{model_resolution}x{model_resolution}.pt", type=str)
    # parser.add_argument('--iteration', default=150, type=int)
    # args = parser.parse_args()

    aligned_image_names = align_images(RAW_DIR, ALIGNED_IMAGE_DIR)

    try:
        if not aligned_image_names:
            print('\nFailed Face Alignment. Abort process.')
            shutil.rmtree(BASE_DIR)  # UUID 디렉터리 삭제
            sys.exit(1)

        aligned_image_name = ALIGNED_IMAGE_DIR + \
            os.listdir(ALIGNED_IMAGE_DIR)[0]
        mask_name, eyes_mask_name, lids_mask_name = precision_eye_masks(
            aligned_image_name, MASK_DIR)

        ingredient_name = ALIGNED_IMAGE_DIR + os.listdir(ALIGNED_IMAGE_DIR)[0]
        random_target_image_index = random.randint(
            0, len(os.listdir(TARGET_SOURCE_DIR))-1)
        target_name = TARGET_SOURCE_DIR + \
            os.listdir(TARGET_SOURCE_DIR)[random_target_image_index]

    except IndexError as e:
        print("Missing file(s).\nCheck if all of source images prepared properly and try again.")
        print(f"Aligned_image_names function: {e}")
        shutil.rmtree(BASE_DIR)  # UUID 디렉터리 삭제
        sys.exit(1)

    final_name = FINAL_IMAGE_DIR + str(rand_uuid) + '.png'

    g_all = nn.Sequential(OrderedDict([('g_mapping', G_mapping()),  # ('truncation', Truncation(avg_latent)),
                                       ('g_synthesis', G_synthesis(resolution=model_resolution))]))

    g_all.load_state_dict(torch.load(
        f"../image_2_style_gan/torch_weight_files/karras2019stylegan-ffhq-{model_resolution}x{model_resolution}.pt", map_location=device))
    g_all.eval()
    g_all.to(device)
    g_mapping, g_synthesis = g_all[0], g_all[1]

    img_0 = image_reader_color(target_name)  # (1,3,1024,1024) -1~1
    img_0 = img_0.to(device)

    img_1 = image_reader_color(ingredient_name)
    img_1 = img_1.to(device)  # (1,3,1024,1024)

    blur_mask0_1 = image_reader_gray(mask_name).to(device)
    blur_mask0_2 = image_reader_gray(eyes_mask_name).to(device)
    blur_mask0_3 = image_reader_gray(lids_mask_name).to(device)
    # blur_mask0_4=image_reader_gray(brows_mask_name).to(device)
    # blur_mask0_5=image_reader_gray(face_mask_name).to(device)
    blur_mask1 = 1-blur_mask0_1
    blur_mask2 = 1-blur_mask0_2
    blur_mask_eyes = blur_mask0_1-blur_mask0_2
    blur_mask_lids = blur_mask0_1-torch.clamp(blur_mask0_3-blur_mask0_2, 0, 1)

    hist_bias = torch.Tensor([0, 0, 0])

    for i in range(3):
        bias = 0
        hist_bias[i] = torch.mean(img_1[0, i, ..., ...]*blur_mask0_1) - torch.mean(img_0[0, i, ..., ...]*blur_mask0_1)
        if hist_bias[i] < 0:
            bias = hist_bias[i] * 77
        print('{:.5f}'.format(hist_bias[i]))
        img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*(15000 + hist_bias[i]*(10 ** 6))), 0, 1) + bias
    
    save_image(img_0, '../image_2_style_gan/source/histadjs.png')
    
    ingredient_eyes = img_1 * blur_mask0_2
    e_mean = []
    for i in range(ingredient_eyes.shape[1]):
        e_mean.append(torch.mean(ingredient_eyes[0, i, ..., ...]))
    idx = e_mean.index(min(e_mean))
    for i in range(ingredient_eyes.shape[1]):
        ingredient_eyes[0, i, ..., ...] = ingredient_eyes[0, idx, ..., ...]
    img_1 = (img_1 * blur_mask2) + ingredient_eyes
    # img_1 = img_1.to(device)  # (1,3,1024,1024)

        # if hist_abs_mean < 0.0001:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*16000), 0, 1)
        # elif hist_abs_mean >= 0.0001 and hist_abs_mean < 0.0009:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*17000), 0, 1)
        # elif hist_abs_mean >= 0.0009 and hist_abs_mean < 0.0015:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*18500), 0, 1)
        # elif hist_abs_mean >= 0.0015 and hist_abs_mean < 0.002:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*20500), 0, 1)
        # elif hist_abs_mean >= 0.002 and hist_abs_mean < 0.0025:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*22500), 0, 1)
        # elif hist_abs_mean >= 0.0025 and hist_abs_mean < 0.003:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*25000), 0, 1)
        # else:
        #     img_0[0, i, ..., ...] = torch.clamp(img_0[0, i, ..., ...] + hist_bias[i]*abs(hist_bias[i]*27500), 0, 1)
    
    # hist_bias_r = torch.mean(
    #     img_1[0, 0, ..., ...]*blur_mask0_1) - torch.mean(img_0[0, 0, ..., ...]*blur_mask0_1)
    # hist_bias_g = torch.mean(
    #     img_1[0, 1, ..., ...]*blur_mask0_1) - torch.mean(img_0[0, 1, ..., ...]*blur_mask0_1)
    # hist_bias_b = torch.mean(
    #     img_1[0, 2, ..., ...]*blur_mask0_1) - torch.mean(img_0[0, 2, ..., ...]*blur_mask0_1)

    # img_0[0, 0, ..., ...] = torch.clamp(
    #     img_0[0, 0, ..., ...] + hist_bias_r*abs(hist_bias_r*19000), 0, 1)
    # img_0[0, 1, ..., ...] = torch.clamp(
    #     img_0[0, 1, ..., ...] + hist_bias_g*abs(hist_bias_g*19000), 0, 1)
    # img_0[0, 2, ..., ...] = torch.clamp(
    #     img_0[0, 2, ..., ...] + hist_bias_b*abs(hist_bias_b*19000), 0, 1)

    MSE_Loss = nn.MSELoss(reduction="mean")
    upsample2d = torch.nn.Upsample(scale_factor=0.5, mode='nearest')

    img_p0 = img_0.clone()  # resize for perceptual net
    img_p0 = upsample2d(img_p0)
    img_p0 = upsample2d(img_p0)  # (1,3,256,256)

    img_p1 = img_1.clone()
    img_p1 = upsample2d(img_p1)
    img_p1 = upsample2d(img_p1)  # (1,3,256,256)

    perceptual_net = VGG16_for_Perceptual(n_layers=[2, 4, 14, 21]).to(
        device)  # conv1_1,conv1_2,conv2_2,conv3_3
    dlatent = torch.zeros((1, 18, 512), requires_grad=True, device=device)
    optimizer = optim.Adam({dlatent}, lr=0.01, betas=(0.9, 0.999), eps=1e-8)

    loss_list = []

    print("Start ---------------------------------------------------------------------------------------")
    # [img_0 : Target IMG] / [img_1 : Ingredient IMG]
    for i in range(150):
        optimizer.zero_grad()
        synth_img = g_synthesis(dlatent)
        synth_img = (synth_img + 1) / 2

        loss_wl0 = caluclate_loss(
            synth_img, img_0, perceptual_net, img_p0, blur_mask_eyes, MSE_Loss, upsample2d)
        loss_wl1 = caluclate_loss(
            synth_img, img_1, perceptual_net, img_p1, blur_mask_lids, MSE_Loss, upsample2d)
        # loss_wl2=caluclate_loss(synth_img,img_1,perceptual_net,img_p1,blur_mask0_2,MSE_Loss,upsample2d)
        loss = loss_wl0 #+ loss_wl1  # + loss_wl2
        loss.backward()

        optimizer.step()

        loss_np = loss.detach().cpu().numpy()
        loss_0 = loss_wl0.detach().cpu().numpy()
        loss_1 = loss_wl1.detach().cpu().numpy()
        # loss_2=loss_wl2.detach().cpu().numpy()

        loss_list.append(loss_np)

        if i % 10 == 0:
            # print("iter{}: loss --{},  loss0 --{},  loss1 --{},  loss2 --{}".format(i, loss_np, loss_0, loss_1, loss_2))
            print("iter{}: loss --{},  loss0 --{},  loss1 --{}".format(i,
                                                                       loss_np, loss_0, loss_1))
            # print("iter{}: loss --{},  loss0 --{}".format(i, loss_np, loss_0))
        elif i == (150 - 1):
            save_image(img_1*blur_mask1 + synth_img*blur_mask0_1, final_name)
            # save_image(synth_img.clamp(0, 1), final_name)

    compare_result = imread(final_name).astype(np.uint8)
    compare_origin = imread(ingredient_name).astype(np.uint8)
    matched = match_histograms(
        compare_result, compare_origin, multichannel=True).astype(np.uint8)
    imsave(final_name, matched)

    origin_name = '{}{}_origin.png'.format(FINAL_IMAGE_DIR, str(rand_uuid))
    os.replace(ingredient_name, origin_name)

    print("Complete ---------------------------------------------------------------------------------------------")

    return origin_name, final_name


def caluclate_loss(synth_img, img, perceptual_net, img_p, blur_mask, MSE_Loss, upsample2d):  # W_l
    # calculate MSE Loss
    mse_loss = MSE_Loss(synth_img*blur_mask.expand(1, 3, 1024, 1024),
                        img*blur_mask.expand(1, 3, 1024, 1024))  # (lamda_mse/N)*||G(w)-I||^2
    # calculate Perceptual Loss
    real_0, real_1, real_2, real_3 = perceptual_net(img_p)
    synth_p = upsample2d(synth_img)  # (1,3,256,256)
    synth_p = upsample2d(synth_p)
    synth_0, synth_1, synth_2, synth_3 = perceptual_net(synth_p)
    # print(synth_0.size(),synth_1.size(),synth_2.size(),synth_3.size())

    perceptual_loss = 0
    blur_mask = upsample2d(blur_mask)
    blur_mask = upsample2d(blur_mask)  # (256,256)

    perceptual_loss += MSE_Loss(synth_0*blur_mask.expand(1,
                                                         64, 256, 256), real_0*blur_mask.expand(1, 64, 256, 256))
    perceptual_loss += MSE_Loss(synth_1*blur_mask.expand(1,
                                                         64, 256, 256), real_1*blur_mask.expand(1, 64, 256, 256))
    blur_mask = upsample2d(blur_mask)
    blur_mask = upsample2d(blur_mask)  # (64,64)
    perceptual_loss += MSE_Loss(synth_2*blur_mask.expand(1,
                                                         256, 64, 64), real_2*blur_mask.expand(1, 256, 64, 64))
    blur_mask = upsample2d(blur_mask)  # (64,64)
    perceptual_loss += MSE_Loss(synth_3*blur_mask.expand(1,
                                                         512, 32, 32), real_3*blur_mask.expand(1, 512, 32, 32))

    return mse_loss+perceptual_loss


# if __name__ == "__main__":
#     model_resolution = 1024
#     parser = argparse.ArgumentParser(
#         description='Find latent representation of reference images using perceptual loss')
#     parser.add_argument('--batch_size', default=1,
#                         help='Batch size for generator and perceptual model', type=int)
#     parser.add_argument('--resolution', default=model_resolution, type=int)
#     parser.add_argument(
#         '--src_im1', default="../image_2_style_gan/source/target/")
#     parser.add_argument(
#         '--src_im2', default="../image_2_style_gan/ingredient/")
#     parser.add_argument('--mask', default="../image_2_style_gan/mask/")
#     parser.add_argument('--weight_file', default="../image_2_style_gan/torch_weight_files/karras2019stylegan-ffhq-{}x{}.pt".format(
#         model_resolution, model_resolution), type=str)
#     parser.add_argument('--iteration', default=150, type=int)

#     args = parser.parse_args()
